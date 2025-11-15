from flask import Blueprint, jsonify

from ..database.repository import find_all_menu_items

bp = Blueprint("menu", __name__)


@bp.get("/menu")
def list_menu_items():
    """Lists all available menu items."""
    menu_list = [item.model_dump() for item in find_all_menu_items()]
    return jsonify(menu_list)
