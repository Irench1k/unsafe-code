from flask import Blueprint, g

from ..auth.decorators import require_auth, restaurant_owns
from ..database.models import MenuItem
from ..database.repository import find_all_menu_items, find_menu_items_by_restaurant
from ..errors import CheekyApiError
from ..utils import (
    created_response,
    get_restaurant_id,
    require_condition,
    success_response,
)
from . import restaurants_service, restaurants_validators

bp = Blueprint("menu", __name__)


@bp.get("/menu")
def list_menu_items():
    """Lists all available menu items."""
    try:
        restaurant_id = get_restaurant_id()
        menu_items = find_menu_items_by_restaurant(restaurant_id)
    except CheekyApiError:
        # It's okay to not have a restaurant ID, just return all menu items
        menu_items = find_all_menu_items()

    return success_response(restaurants_validators.serialize_menu_items(menu_items))


@bp.post("/menu/<int:restaurant_id>")
@require_auth(["restaurant_api_key"])
def create_menu_item(restaurant_id: int):
    """Convenience endpoint for creating a menu item via /menu."""
    require_condition(
        getattr(g, "restaurant_id", None) == restaurant_id,
        "Unauthorized",
    )
    fields = restaurants_validators.validate_menu_item_fields(require_name=True, require_price=True)
    menu_item = restaurants_service.create_menu_item_for_restaurant(restaurant_id, fields)
    return created_response(restaurants_validators.serialize_menu_item(menu_item))


@bp.patch("/menu/<int:item_id>")
@require_auth(["restaurant_api_key"])
@restaurant_owns(MenuItem, "item_id")
def update_menu_item(item_id: int):
    """Convenience endpoint for updating a menu item via /menu."""
    menu_item = restaurants_validators.validate_menu_item_exists(item_id)
    fields = restaurants_validators.validate_menu_item_fields(require_any=True)
    menu_item = restaurants_service.apply_menu_item_changes(menu_item, fields)
    return success_response(restaurants_validators.serialize_menu_item(menu_item))
