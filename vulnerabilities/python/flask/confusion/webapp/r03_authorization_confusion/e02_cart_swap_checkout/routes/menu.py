from flask import Blueprint

from ..database.repository import find_all_menu_items, find_menu_items_by_restaurant, find_restaurant_by_id
from ..database.services import serialize_menu_items
from ..utils import get_restaurant_id, require_condition, success_response

bp = Blueprint("menu", __name__)


@bp.get("/menu")
def list_menu_items():
    """Lists all available menu items."""
    restaurant_id = get_restaurant_id()
    if restaurant_id is not None:
        restaurant = find_restaurant_by_id(restaurant_id)
        require_condition(restaurant, f"Restaurant {restaurant_id} not found")
        menu_items = find_menu_items_by_restaurant(restaurant_id)
    else:
        menu_items = find_all_menu_items()

    return success_response(serialize_menu_items(menu_items))
