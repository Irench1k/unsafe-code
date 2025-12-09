import logging

from flask import g

from ..database.models import Restaurant
from ..utils import resolve_restaurant_id

logger = logging.getLogger(__name__)


def get_trusted_restaurant() -> Restaurant | None:
    """
    Get the restaurant for the current request context.

    Resolution order:
    1. Authorized restaurant (set by @require_restaurant_owner decorator)
    2. Restaurant ID from request (query param, JSON body, path)
    3. Restaurant manager's own restaurant (from API key auth)
    """
    from ..database.repository import find_restaurant_by_id

    # Return the authorized restaurant if it exists (set by decorator)
    if g.get("authorized_restaurant"):
        return g.authorized_restaurant

    # Get the restaurant from the request context
    restaurant_id = resolve_restaurant_id()
    if restaurant_id:
        return find_restaurant_by_id(restaurant_id)

    # Fall back to restaurant manager's restaurant (from API key auth)
    if g.get("restaurant_manager"):
        from ..database.repository import find_restaurant_by_id

        return find_restaurant_by_id(g.restaurant_manager)

    return None


def get_trusted_restaurant_id() -> int | None:
    """Get the restaurant ID for the current request context."""
    if g.get("authorized_restaurant"):
        return g.authorized_restaurant.id

    restaurant_id = resolve_restaurant_id()
    if restaurant_id:
        return restaurant_id

    # Fall back to API key's restaurant
    if g.get("restaurant_manager"):
        return g.restaurant_manager

    return None
