import datetime
from decimal import Decimal
from uuid import uuid4

import jwt
from envelopes import SMTP, Envelope
from flask import jsonify, request

from .errors import CheekyApiError

JWT_SECRET = str(uuid4())


# ============================================================
# INPUT PARSING UTILITIES
# ============================================================
#
# v405 Refactoring: Consume-Once Parameter Access (JSON-Only)
# -----------------------------------------------------------
# After discovering bugs where parameters were read multiple times
# with potentially different results, we now use a "consume once"
# pattern for JSON body access:
#
# - consume_param(): Returns value and removes it from JSON body
# - For scalars: removes the entire key
# - For arrays: pops the first element (supports batch operations)
#
# This ensures each parameter read is intentional and prevents
# accidental double-reads from returning inconsistent values.
#
# NOTE: This is part of our migration to JSON-only APIs. Restaurant
# and menu endpoints now require JSON bodies exclusively. Other
# endpoints (orders, carts) still use legacy query/form patterns.
#
# @unsafe {
#     "vuln_id": "v405",
#     "severity": "high",
#     "category": "cardinality-confusion",
#     "description": "Consume-once pattern with arrays causes first/second value desync",
#     "cwe": "CWE-1289"
# }


def consume_param(name: str) -> str | int | bool | None:
    """
    Consume and return a parameter value from JSON body.

    This is the SAFE way to read parameters - ensures each value is only
    used once, preventing bugs where the same parameter is read multiple
    times with potentially different interpretations.

    Returns None if parameter not found, already consumed, or not a JSON request.
    """
    if not request.is_json or not isinstance(request.json, dict):
        return None

    if name not in request.json:
        return None

    value = request.json[name]

    # Batch operations: pop first element
    if isinstance(value, list):
        if len(value) > 0:
            return value.pop(0)
        # Empty array - remove the key entirely
        del request.json[name]
        return None

    # Scalars: consume entire value
    del request.json[name]
    return value


def consume_string(name: str, *, required: bool = False) -> str | None:
    """Consume and validate a string parameter from JSON body."""
    value = consume_param(name)
    if value is None:
        if required:
            raise CheekyApiError(f"{name} is required")
        return None
    if not isinstance(value, str):
        raise CheekyApiError(f"{name} must be a string")
    value = value.strip()
    if required and not value:
        raise CheekyApiError(f"{name} cannot be empty")
    return value if value else None


def consume_int(name: str, *, required: bool = False, positive: bool = False) -> int | None:
    """Consume and validate an integer parameter from JSON body."""
    value = consume_param(name)
    if value is None:
        if required:
            raise CheekyApiError(f"{name} is required")
        return None
    try:
        int_value = int(value)
    except (TypeError, ValueError):
        raise CheekyApiError(f"{name} must be an integer") from None
    if positive and int_value <= 0:
        raise CheekyApiError(f"{name} must be positive")
    return int_value


def consume_decimal(name: str, *, required: bool = False, positive: bool = False) -> Decimal | None:
    """Consume and validate a decimal parameter from JSON body."""
    value = consume_param(name)
    if value is None:
        if required:
            raise CheekyApiError(f"{name} is required")
        return None
    if not isinstance(value, (int, float, str)):
        raise CheekyApiError(f"{name} must be a number")
    try:
        decimal_value = Decimal(str(value)).quantize(Decimal("0.01"))
    except Exception:
        raise CheekyApiError(f"{name} must be a valid decimal") from None
    if positive and decimal_value <= 0:
        raise CheekyApiError(f"{name} must be positive")
    return decimal_value


def consume_boolean(name: str, *, required: bool = False) -> bool | None:
    """Consume and validate a boolean parameter from JSON body."""
    value = consume_param(name)
    if value is None:
        if required:
            raise CheekyApiError(f"{name} is required")
        return None
    if not isinstance(value, bool):
        raise CheekyApiError(f"{name} must be a boolean")
    return value


def consume_int_list(name: str, *, required: bool = False, min_length: int = 0) -> list[int] | None:
    """Consume and validate a list of integers from JSON body (consumes entire list)."""
    if not request.is_json or not isinstance(request.json, dict):
        if required:
            raise CheekyApiError(f"{name} is required")
        return None

    if name not in request.json:
        if required:
            raise CheekyApiError(f"{name} is required")
        return None

    # For lists, consume the ENTIRE list at once (not element-by-element)
    value = request.json.pop(name)

    if not isinstance(value, list):
        raise CheekyApiError(f"{name} must be a list")
    if len(value) < min_length:
        raise CheekyApiError(f"{name} must have at least {min_length} items")
    if not all(isinstance(item, int) for item in value):
        raise CheekyApiError(f"{name} must be a list of integers")
    return value


# ============================================================
# LEGACY INPUT PARSING (for non-JSON endpoints)
# ============================================================
# These functions are used by older endpoints (orders, carts, etc.)
# that still accept query params and form data. New restaurant/menu
# endpoints should use consume_* functions above.


def get_param(name: str) -> str | None:
    """
    Get a string parameter from anywhere in the request.

    LEGACY: Use consume_* functions for new JSON-only endpoints.

    Checks in order: query args, JSON body, form data.
    Returns None if parameter not found in any location.
    """
    if name in request.args:
        return request.args.get(name)

    if request.is_json and isinstance(request.json, dict) and name in request.json:
        return request.json.get(name)

    if name in request.form:
        return request.form.get(name)

    return None


def get_list_param(name: str) -> list[str]:
    """
    Get a list of strings from anywhere in the request.

    LEGACY: Use consume_int_list for new JSON-only endpoints.
    """
    if request.is_json:
        if isinstance(request.json, dict) and name in request.json:
            value = request.json.get(name)
            if isinstance(value, list) and all(isinstance(item, str) for item in value):
                return value
        return []

    if name in request.form:
        return request.form.getlist(name)

    return []


def _parse_id(value, name: str = "id") -> int:
    """Parse a value as a positive integer."""
    try:
        int_value = int(value)
    except (TypeError, ValueError):
        raise CheekyApiError(f"{name} must be an integer") from None

    if int_value < 0:
        raise CheekyApiError(f"{name} can't be negative")
    return int_value


def require_int_param(name: str) -> int:
    """
    Get a required integer parameter from the request.

    LEGACY: Use consume_int for new JSON-only endpoints.
    """
    value = get_param(name)
    if value is None:
        raise CheekyApiError(f"{name} is required")
    return _parse_id(value, name)


def get_int_param(name: str, default: int | None = None) -> int | None:
    """
    Get an optional integer parameter from the request.

    LEGACY: Use consume_int for new JSON-only endpoints.
    """
    value = get_param(name)
    if value is None:
        return default
    return _parse_id(value, name)


def get_decimal_param(name: str, default: Decimal | None = None) -> Decimal | None:
    """
    Get an optional decimal parameter from the request.

    LEGACY: Use consume_decimal for new JSON-only endpoints.
    """
    value = get_param(name)
    if value is None:
        return default
    try:
        return Decimal(str(value)).quantize(Decimal("1.00"))
    except Exception:
        return default


def get_boolean_param(name: str, default: bool | None = None) -> bool | None:
    """
    Get an optional boolean parameter from the request.

    LEGACY: Use consume_boolean for new JSON-only endpoints.
    """
    value = get_param(name)
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    normalized = str(value).strip().lower()
    if normalized in {"true", "1", "yes", "on"}:
        return True
    if normalized in {"false", "0", "no", "off"}:
        return False
    return default


# ============================================================
# AUTHORIZATION UTILITIES
# ============================================================


def require_ownership(owner_id: int, current_user_id: int, resource_name: str = "Resource"):
    """
    Verify that the current user owns the resource.

    Raises CheekyApiError if the owner_id does not match the current_user_id.
    """
    if owner_id != current_user_id:
        raise CheekyApiError(f"{resource_name} does not belong to user")


def require_condition(condition: bool, message: str):
    if not condition:
        raise CheekyApiError(message)


# ============================================================
# RESTAURANT RESOLUTION
# ============================================================
def _get_restaurant_id() -> int | None:
    """
    Consume and return the restaurant_id parameter.

    This is the SAFE way to get restaurant context - prevents bugs where
    restaurant_id is read multiple times with different values.
    """
    value = consume_param("restaurant_id")
    if value is not None:
        try:
            return int(value)
        except (TypeError, ValueError):
            return None
    return None


def resolve_restaurant_id() -> int | None:
    """
    Auto-detect restaurant ID from request context.

    Priority:
    1. Path parameter (e.g., /restaurants/<restaurant_id>/...)
    2. Consumed from JSON body via _get_restaurant_id()
    """
    # Manager endpoints: restaurant_id in path, checked by @require_restaurant_{manager,owner}
    if request.view_args and "restaurant_id" in request.view_args:
        try:
            return int(request.view_args["restaurant_id"])
        except (TypeError, ValueError):
            return None

    # Other endpoints: consume from query/body
    return _get_restaurant_id()


# ============================================================
# DOMAIN-SPECIFIC UTILITIES
# ============================================================
def _generate_user_verification_token(email: str) -> str:
    """Generate a stateless verification token for the given user's email."""
    expires_at = datetime.datetime.now(tz=datetime.UTC) + datetime.timedelta(minutes=30)
    return jwt.encode(
        {
            "iss": "app.cheeky.sea",
            "aud": "user_verification",
            "email": email,
            "exp": expires_at,
        },
        JWT_SECRET,
        algorithm="HS256",
    )


def generate_domain_verification_token(
    name: str | None,
    description: str | None,
    domain: str | None,
    owner: str | None,
    restaurant_id: int | None,
) -> str:
    """Generate a stateless verification token for the given domain's admin email."""
    expires_at = datetime.datetime.now(tz=datetime.UTC) + datetime.timedelta(minutes=30)
    return jwt.encode(
        {
            "iss": "app.cheeky.sea",
            "aud": "domain_verification",
            "name": name,
            "description": description,
            "domain": domain,
            "owner": owner,
            "restaurant_id": restaurant_id,
            "exp": expires_at,
        },
        JWT_SECRET,
        algorithm="HS256",
    )


def verify_and_decode_token(token: str, audience: str) -> dict | None:
    """Verify the verification token and return the decoded token."""
    try:
        return jwt.decode(
            token,
            JWT_SECRET,
            algorithms=["HS256"],
            audience=audience,
            issuer="app.cheeky.sea",
            options={"require": ["iss", "aud"]},
        )
    except jwt.InvalidTokenError:
        return None


VERIFICATION_EMAIL_TEMPLATE = """
Thank you for registering at Cheeky Sea!

Click the link to verify your registration: https://app.cheeky.sea/verify?token={token}

If the link doesn't work, copy and paste the following token:

{token}

If you have not initiated this registration, please ignore this email!

Kind regards,
The Cheeky Sea Team
"""


def send_user_verification_email(email: str):
    """Send a verification email to the user."""
    token = _generate_user_verification_token(email)

    envelope = Envelope(
        from_addr="no-reply@app.cheeky.sea",
        to_addr=email,
        subject="Verify your registration at Cheeky Sea!",
        text_body=VERIFICATION_EMAIL_TEMPLATE.format(token=token),
    )
    smtp = SMTP(host="mailpit", port=1025)
    smtp.send(envelope)


DOMAIN_VERIFICATION_EMAIL_TEMPLATE = """
Thank you for registering your restaurant at Cheeky Sea!

Click the link to verify your domain ownership: https://app.cheeky.sea/verify-restaurant?token={token}

If the link doesn't work, copy and paste the following token:

{token}

If you have not initiated this registration, please ignore this email!

Kind regards,
The Cheeky Sea Team
"""


def send_domain_verification_email(domain: str, verification_email: str, token: str):
    """Send a domain verification email for restaurant registration."""
    envelope = Envelope(
        from_addr="no-reply@app.cheeky.sea",
        to_addr=verification_email,
        subject=f"Verify your domain {domain} at Cheeky Sea!",
        text_body=DOMAIN_VERIFICATION_EMAIL_TEMPLATE.format(token=token),
    )
    smtp = SMTP(host="mailpit", port=1025)
    smtp.send(envelope)


# ============================================================
# RESPONSE UTILITIES
# ============================================================
def success_response(data: dict, status_code: int = 200) -> tuple[dict, int]:
    """Return a success response with the given data."""
    return jsonify(data), status_code


def error_response(message: str, status_code: int = 400) -> tuple[dict, int]:
    """Return an error response with the given message."""
    return jsonify({"error": message}), status_code


def created_response(response, status=201) -> tuple[dict, int]:
    """Return a created response with the given response."""
    return jsonify(response), status


def not_found_response() -> tuple[dict, int]:
    """Return a not found response."""
    return jsonify({"error": "Not found"}), 404
