import datetime
from collections.abc import Iterable
from decimal import Decimal
from uuid import uuid4

import jwt
from envelopes import SMTP, Envelope
from flask import jsonify, request

from .database.models import CartItem, OrderItem
from .database.repository import find_menu_item_by_id
from .errors import CheekyApiError

DELIVERY_FEE = Decimal("5.00")
FREE_DELIVERY_ABOVE = Decimal("25.00")
JWT_SECRET = str(uuid4())


def _menu_item_price(item_id: str | int) -> Decimal | None:
    """Returns the current price for an available menu item."""
    if not item_id:
        return None

    try:
        normalized_id = int(item_id)
    except (TypeError, ValueError):
        return None

    menu_item = find_menu_item_by_id(normalized_id)
    if not menu_item or not menu_item.available:
        return None

    return menu_item.price


def _calculate_delivery_fee(total_price: Decimal) -> Decimal:
    """Adds a flat delivery fee unless the order crosses the free-shipping threshold."""
    if total_price > FREE_DELIVERY_ABOVE:
        return Decimal("0.00")
    return DELIVERY_FEE


def check_cart_price_and_delivery_fee(items: Iterable[CartItem]) -> tuple[Decimal, Decimal]:
    """
    Validates that all cart items are orderable and returns their price and delivery fee.

    Returns (None, None) as a signal to the caller when any menu item is missing or unavailable.
    """
    total_price = Decimal("0.00")
    for item in items:
        price = _menu_item_price(item.item_id)
        if price is None:
            return None, None
        total_price += price

    return total_price, _calculate_delivery_fee(total_price)


def parse_as_decimal(value: str) -> Decimal | None:
    try:
        return Decimal(value)
    except Exception:
        return None


def parse_as_int(value: str) -> int | None:
    try:
        return int(value)
    except Exception:
        return None


def get_request_parameter(parameter):
    parameter_in_args = request.args.get(parameter)
    parameter_in_json = (
        request.is_json and isinstance(request.json, dict) and request.json.get(parameter)
    )
    parameter_in_form = request.form.get(parameter)

    return parameter_in_args or parameter_in_json or parameter_in_form


def get_restaurant_id() -> int:
    restaurant_id = parse_as_int(get_request_parameter("restaurant_id"))
    if restaurant_id is None:
        raise CheekyApiError("Restaurant ID is required")
    return restaurant_id


def _generate_verification_token(email: str) -> str:
    """Generate a stateless verification token for the given email."""
    expires_at = datetime.datetime.now(tz=datetime.UTC) + datetime.timedelta(minutes=30)
    return jwt.encode(
        {
            "email": email,
            "exp": expires_at,
        },
        JWT_SECRET,
        algorithm="HS256",
    )


def get_email_from_token(token: str) -> str | None:
    """Extract the email from the token pre-verification."""
    decoded_token = verify_and_decode_token(token)
    if not decoded_token:
        return None
    return decoded_token.get("email")


def verify_and_decode_token(token: str) -> dict | None:
    """Verify the verification token and return the decoded token."""
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
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


def send_verification_email(email: str):
    """Send a verification email to the user."""
    token = _generate_verification_token(email)

    envelope = Envelope(
        from_addr="no-reply@app.cheeky.sea",
        to_addr=email,
        subject="Verify your registration at Cheeky Sea!",
        text_body=VERIFICATION_EMAIL_TEMPLATE.format(token=token),
    )
    smtp = SMTP(host="mailpit", port=1025)
    smtp.send(envelope)

    return jsonify({"status": "verification_email_sent", "email": email}), 200
