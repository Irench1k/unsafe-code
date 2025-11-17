from flask import Blueprint, jsonify

from ..database.repository import find_all_menu_items, find_menu_items_by_restaurant
from ..database.services import serialize_menu_items
from ..errors import CheekyApiError
from ..utils import get_restaurant_id

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

    return jsonify(serialize_menu_items(menu_items))
