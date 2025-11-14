import datetime
from collections.abc import Iterable
from decimal import Decimal
from uuid import uuid4

import jwt
from flask import request

from .database import get_menu_item, get_user
from .models import OrderItem

DELIVERY_FEE = Decimal("5.00")
FREE_DELIVERY_ABOVE = Decimal("25.00")
JWT_SECRET = str(uuid4())


def _menu_item_price(item_id: str) -> Decimal | None:
    """Returns the current price for an available menu item."""
    if not item_id:
        return None

    menu_item = get_menu_item(item_id)
    if not menu_item or not menu_item.available:
        return None

    return menu_item.price


def _calculate_delivery_fee(total_price: Decimal) -> Decimal:
    """Adds a flat delivery fee unless the order crosses the free-shipping threshold."""
    if total_price > FREE_DELIVERY_ABOVE:
        return Decimal("0.00")
    return DELIVERY_FEE


def check_cart_price_and_delivery_fee(item_ids: Iterable[str]) -> tuple[Decimal, Decimal]:
    """
    Validates that all cart items are orderable and returns their price and delivery fee.

    Returns (None, None) as a signal to the caller when any menu item is missing or unavailable.
    """
    total_price = Decimal("0.00")
    for item_id in item_ids:
        price = _menu_item_price(item_id)
        if price is None:
            return None, None
        total_price += price

    return total_price, _calculate_delivery_fee(total_price)


def convert_item_ids_to_order_items(item_ids: Iterable[str]) -> list[OrderItem]:
    """
    Converts item IDs to OrderItem snapshots so invoices stay stable even if prices change later.
    """
    order_items: list[OrderItem] = []
    for item_id in item_ids:
        menu_item = get_menu_item(item_id)
        if not menu_item:
            continue
        order_items.append(OrderItem(item_id=item_id, name=menu_item.name, price=menu_item.price))
    return order_items


def parse_as_decimal(value: str) -> Decimal | None:
    try:
        return Decimal(value)
    except Exception:
        return None


def get_request_parameter(parameter):
    parameter_in_args = request.args.get(parameter)
    parameter_in_json = (
        request.is_json and isinstance(request.json, dict) and request.json.get(parameter)
    )
    parameter_in_form = request.form.get(parameter)

    return parameter_in_args or parameter_in_json or parameter_in_form


def generate_verification_token(email: str) -> str:
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


def _verify_and_decode_token(token: str) -> str | None:
    """Verify the verification token and return the decoded token."""
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        print("The token has expired!")
    except jwt.InvalidSignatureError:
        print("The token has an invalid signature!")
    except jwt.InvalidTokenError:
        print("The token is invalid!")
    return None


def verify_user_verification_token(token: str) -> bool:
    """Check that the token is valid, and not expired, and does not belong to existing user."""
    decoded_token = _verify_and_decode_token(token)
    if not decoded_token:
        return False

    email = decoded_token.get("email")
    if not email:
        print(f"The token was signed correctly, but there's no email! {token}")
        return False

    if get_user(email):
        print(f"The token belongs to an existing user: {get_user(email).user_id}")
        return False

    return True


def send_verification_email(email: str, token: str):
    """Send a verification email to the user."""
    # TODO: Implement this
    print(f"Sending verification email to {email} with token {token}")
