from flask import Blueprint, g

from ..auth.decorators import require_auth, restaurant_owns
from ..database.models import MenuItem
from ..database.repository import find_all_menu_items, find_menu_items_by_restaurant
from ..database.services import serialize_menu_item, serialize_menu_items
from ..errors import CheekyApiError
from ..utils import (
    created_response,
    get_restaurant_id,
    require_condition,
    success_response,
)
from .menu_management import (
    create_menu_item_from_request,
    update_menu_item_from_request,
)

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

    return success_response(serialize_menu_items(menu_items))


@bp.post("/menu/<int:restaurant_id>")
@require_auth(["restaurant_api_key"])
def create_menu_item(restaurant_id: int):
    """Convenience endpoint for creating a menu item via /menu."""
    require_condition(
        getattr(g, "restaurant_id", None) == restaurant_id,
        "Unauthorized",
    )
    menu_item = create_menu_item_from_request(restaurant_id)
    return created_response(serialize_menu_item(menu_item))


@bp.patch("/menu/<int:item_id>")
@require_auth(["restaurant_api_key"])
@restaurant_owns(MenuItem, "item_id")
def update_menu_item(item_id: int):
    """Convenience endpoint for updating a menu item via /menu."""
    menu_item = update_menu_item_from_request(item_id)
    return success_response(serialize_menu_item(menu_item))
