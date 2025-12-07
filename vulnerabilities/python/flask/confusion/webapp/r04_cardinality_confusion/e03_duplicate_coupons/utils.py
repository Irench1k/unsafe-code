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
def get_param(name: str) -> str | None:
    """
    Get a string parameter from anywhere in the request.

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


def get_list_param(name: str) -> list[str] | None:
    """Get a list of strings from anywhere in the request."""
    # If json, expect a list of strings
    if request.is_json:
        if isinstance(request.json, dict) and name in request.json:
            value = request.json.get(name)
            if isinstance(value, list) and all(isinstance(item, str) for item in value):
                return value
        return []

    # If form, expect repeated parameters
    if name in request.form:
        return request.form.getlist(name)

    return []


def parse_id(value: str, name: str = "id") -> int:
    """Parse a string as a positive integer."""
    try:
        int_value = int(value)
    except (TypeError, ValueError):
        raise CheekyApiError(f"{name} must be an integer") from None

    if int_value < 0:
        raise ValueError(f"{name} can't be negative")
    return int_value


def require_int_param(name: str) -> int:
    """
    Get a required integer parameter from the request.

    Checks query args, JSON body, and form data.
    Raises CheekyApiError if parameter is missing or not a valid positive integer.
    """
    value = get_param(name)
    if value is None:
        raise CheekyApiError(f"{name} is required")
    return parse_id(value, name)


def get_int_param(name: str, default: int | None = None) -> int | None:
    """Get an optional integer parameter from anywhere in the request."""
    value = get_param(name)
    if value is None:
        return default
    return parse_id(value, name)


def get_decimal_param(name: str, default: Decimal | None = None) -> Decimal | None:
    """Get an optional decimal parameter from anywhere in the request."""
    value = get_param(name)
    if value is None:
        return default
    try:
        return Decimal(value).quantize(Decimal("1.00"))
    except Exception:
        return default


def get_boolean_param(name: str, default: bool | None = None) -> bool | None:
    """Get an optional boolean parameter from anywhere in the request."""
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
# DOMAIN-SPECIFIC UTILITIES
# ============================================================
def get_restaurant_id() -> int:
    """Get the restaurant ID from the request."""
    return require_int_param("restaurant_id")


def bind_to_restaurant() -> int | None:
    """
    Auto-detect restaurant ID from any request container.

    Sandy's new helper that inspects ALL containers (query, form, JSON body)
    to support different clients (SDK, mobile app, manager UI).

    @unsafe {
        "vuln_id": "v304",
        "severity": "high",
        "category": "authorization-confusion",
        "description": "Helper inspects all request containers while decorator only checks query",
        "cwe": "CWE-863"
    }
    """
    # Check all containers - this is the vulnerability!
    # The decorator only checks query params, but this helper checks everything
    restaurant_id_str = get_param("restaurant_id")
    if restaurant_id_str:
        try:
            return int(restaurant_id_str)
        except (TypeError, ValueError):
            return None
    return None


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
