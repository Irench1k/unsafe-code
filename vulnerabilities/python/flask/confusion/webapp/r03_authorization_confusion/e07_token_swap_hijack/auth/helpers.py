import logging

from flask import g

from ..database.models import Restaurant
from ..database.repository import find_order_by_id, find_restaurant_by_id
from ..database.services import get_current_user
from ..errors import CheekyApiError
from ..utils import verify_and_decode_token

logger = logging.getLogger(__name__)


def verify_user_registration(token: str) -> bool:
    """Check that the token is valid, and not expired, and does not belong to existing user."""
    decoded_token = verify_and_decode_token(token)
    if not decoded_token:
        return False

    email = decoded_token.get("email")
    if not email:
        logger.warning("Token missing email field")
        return False

    return True


def get_authenticated_restaurant() -> Restaurant | None:
    restaurant_id = g.get("restaurant_id")
    return find_restaurant_by_id(restaurant_id) if restaurant_id else None


def has_access_to_order(order_id: int) -> bool:
    """Checks if the user or restaurant has access to the order."""
    order = find_order_by_id(order_id)
    if not order:
        raise CheekyApiError("Order not found")

    user = get_current_user()
    restaurant = get_authenticated_restaurant()

    if not user and not restaurant:
        raise CheekyApiError("Customer credentials or restaurant API key is required")

    return order.user_id == user.id if user else order.restaurant_id == restaurant.id
