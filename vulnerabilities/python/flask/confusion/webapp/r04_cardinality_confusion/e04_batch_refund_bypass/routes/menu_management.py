"""
Shared helpers for menu management endpoints.
"""

from ..database.repository import find_menu_item_by_id, find_restaurant_by_id
from ..database.services import apply_menu_item_changes, create_menu_item_for_restaurant
from ..errors import CheekyApiError
from ..utils import get_boolean_param, get_decimal_param, get_param, require_condition


def collect_menu_item_fields(
    *,
    require_name: bool = False,
    require_price: bool = False,
    require_any: bool = False,
) -> dict:
    """Normalize menu item payload and enforce requirements."""
    fields: dict = {}

    name = get_param("name")
    if name is not None:
        require_condition(name.strip(), "name cannot be empty")
        fields["name"] = name
    elif require_name:
        raise CheekyApiError("name is required")

    price_raw = get_param("price")
    if price_raw is not None:
        price = get_decimal_param("price")
        require_condition(price is not None, "price must be a decimal value")
        require_condition(price > 0, "price must be positive")
        fields["price"] = price
    elif require_price:
        raise CheekyApiError("price is required")

    available_raw = get_param("available")
    if available_raw is not None:
        available = get_boolean_param("available")
        require_condition(available is not None, "available must be a boolean value")
        fields["available"] = available

    if require_any:
        require_condition(bool(fields), "No fields provided")

    return fields


def create_menu_item_from_request(restaurant_id: int):
    """Create a menu item for the given restaurant using current request payload."""
    restaurant = find_restaurant_by_id(restaurant_id)
    require_condition(restaurant, f"Restaurant {restaurant_id} not found")

    fields = collect_menu_item_fields(require_name=True, require_price=True)
    return create_menu_item_for_restaurant(restaurant_id, fields)


def update_menu_item_from_request(item_id: int):
    """Update a menu item using current request payload."""
    menu_item = find_menu_item_by_id(item_id)
    require_condition(menu_item, f"Menu item {item_id} not found")

    fields = collect_menu_item_fields(require_any=True)
    return apply_menu_item_changes(menu_item, fields)
