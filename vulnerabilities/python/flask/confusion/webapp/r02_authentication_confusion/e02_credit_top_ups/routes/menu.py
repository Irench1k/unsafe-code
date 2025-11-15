from flask import Blueprint, jsonify

from ..database.repository import find_all_menu_items
from ..database.services import serialize_menu_items

bp = Blueprint("menu", __name__)


@bp.get("/menu")
def list_menu_items():
    """Lists all available menu items."""
    menu_items = find_all_menu_items()
    return jsonify(serialize_menu_items(menu_items))
