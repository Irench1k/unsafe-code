"""Menu Controller - public menu endpoints and convenience API for restaurants.

v405 Migration: All mutation endpoints now require JSON bodies exclusively.
The @bp.before_request hook enforces this for POST/PATCH/PUT/DELETE methods.

NOTE: The /menu endpoints are a "convenience API" that was added later to allow
restaurant managers to manage menus without the /restaurants/<id>/menu prefix.
Some endpoints here were copied from restaurants.py but lack the full
@require_restaurant_manager decorator chain.
"""

import logging

from flask import Blueprint, g

from ..auth.decorators import require_auth
from ..auth.helpers import get_trusted_restaurant_id
from ..auth.middleware import require_json_for_mutations
from ..database.repository import (
    create_restaurant_menu_item,
    find_all_menu_items,
    find_menu_item_by_id,
    update_restaurant_menu_item,
)
from ..utils import (
    created_response,
    not_found_response,
    require_condition,
    success_response,
)
from .restaurants_validators import (
    serialize_menu_item,
    serialize_menu_items,
    validate_menu_item_fields,
)

bp = Blueprint("menu", __name__)

logger = logging.getLogger(__name__)


@bp.before_request
def _require_json_for_mutations():
    require_json_for_mutations()


@bp.get("/menu")
def list_menu_items():
    """Lists all available menu items (public endpoint)."""
    menu_items = find_all_menu_items()
    return success_response(serialize_menu_items(menu_items))


@bp.get("/menu/<int:item_id>")
def get_menu_item(item_id: int):
    """Get a single menu item by ID (public endpoint)."""
    menu_item = find_menu_item_by_id(item_id)
    return success_response(serialize_menu_item(menu_item)) if menu_item else not_found_response()


@bp.post("/menu/<int:restaurant_id>")
@require_auth(["restaurant_api_key"])
def create_menu_item_route(restaurant_id: int):
    """
    Create a menu item for a restaurant.

    The restaurant_id in the path is for routing only.
    Actual restaurant association uses get_trusted_restaurant_id().
    """
    restaurant_id = get_trusted_restaurant_id()
    require_condition(restaurant_id == g.restaurant_manager, "Unauthorized")

    name, price, available = validate_menu_item_fields(require_name=True, require_price=True)
    menu_item = create_restaurant_menu_item(name, price, available)
    return created_response(serialize_menu_item(menu_item))


@bp.patch("/menu/<int:item_id>")
@require_auth(["restaurant_api_key"])
def update_menu_item_route(item_id: int):
    """
    Update a menu item.

    Copied from restaurants.py but without the @require_restaurant_manager decorator.
    Developer added manual authorization check instead.

    @unsafe {
        "vuln_id": "v405",
        "severity": "high",
        "category": "cardinality-confusion",
        "description": "Authorization check consumes first restaurant_id, update consumes second",
        "cwe": "CWE-1289",
        "attack_vector": "Send restaurant_id as array: [attacker_id, victim_id]",
        "impact": "Modify menu items belonging to other restaurants"
    }
    """
    restaurant_id = get_trusted_restaurant_id()
    require_condition(restaurant_id == g.restaurant_manager, "Unauthorized")

    name, price, available = validate_menu_item_fields(require_any=True)
    menu_item = update_restaurant_menu_item(item_id, name, price, available)

    return success_response(serialize_menu_item(menu_item)) if menu_item else not_found_response()
