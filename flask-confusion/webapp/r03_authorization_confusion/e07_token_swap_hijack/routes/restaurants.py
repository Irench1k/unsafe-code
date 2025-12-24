"""
Restaurant routes - endpoints for managing and viewing restaurants.
"""

from typing import Any

from flask import Blueprint, g

from ..auth.decorators import (
    require_auth,
    require_restaurant_owner,
    restaurant_owns,
    send_and_verify_domain_token,
)
from ..database.models import MenuItem
from ..database.repository import (
    find_all_restaurants,
    find_menu_items_by_restaurant,
    find_restaurant_by_id,
    find_restaurant_users,
)
from ..database.services import (
    create_restaurant,
    serialize_menu_item,
    serialize_menu_items,
    serialize_restaurant,
    serialize_restaurant_creation,
    serialize_restaurant_users,
    serialize_restaurants,
    update_restaurant,
)
from ..utils import (
    created_response,
    get_param,
    require_condition,
    require_ownership,
    success_response,
)
from .menu_management import (
    create_menu_item_from_request,
    update_menu_item_from_request,
)

bp = Blueprint("restaurants", __name__, url_prefix="/restaurants")


@bp.get("")
def list_restaurants():
    """Lists all restaurants in the system."""
    restaurants = find_all_restaurants()
    return success_response(serialize_restaurants(restaurants))


@bp.get("/<int:restaurant_id>/")
def get_restaurant(restaurant_id: int):
    """Get a restaurant."""
    restaurant = find_restaurant_by_id(restaurant_id)
    require_condition(restaurant, f"Restaurant {restaurant_id} not found")
    return success_response(serialize_restaurant(restaurant))


@bp.get("/<int:restaurant_id>/users")
@require_auth(["restaurant_api_key"])
def list_users(restaurant_id: int):
    """List all users in the system with a matching email address."""
    restaurant = find_restaurant_by_id(restaurant_id)
    require_condition(restaurant, f"Restaurant {restaurant_id} not found")
    require_ownership(restaurant.id, g.restaurant_id, "restaurant")

    users = find_restaurant_users(restaurant_id)
    return success_response(serialize_restaurant_users(users))


@bp.get("/<int:restaurant_id>/menu")
def list_menu_items(restaurant_id: int):
    """Lists all menu items for a restaurant."""
    restaurant = find_restaurant_by_id(restaurant_id)
    require_condition(restaurant, f"Restaurant {restaurant_id} not found")

    menu_items = find_menu_items_by_restaurant(restaurant_id)
    return success_response(serialize_menu_items(menu_items))


@bp.patch("/<int:restaurant_id>/menu/<int:item_id>")
@require_auth(["restaurant_api_key"])
@restaurant_owns(MenuItem, "item_id")
def update_menu_item(restaurant_id: int, item_id: int):
    """Update a menu item."""
    menu_item = update_menu_item_from_request(item_id)
    return success_response(serialize_menu_item(menu_item))


@bp.post("/<int:restaurant_id>/menu")
@require_auth(["restaurant_api_key"])
def create_menu_item(restaurant_id: int):
    """Create a new menu item for the authenticated restaurant."""
    require_condition(
        getattr(g, "restaurant_id", None) == restaurant_id,
        "Unauthorized",
    )
    menu_item = create_menu_item_from_request(restaurant_id)
    return created_response(serialize_menu_item(menu_item))


@bp.post("")
@require_auth(["customer"])
@send_and_verify_domain_token
def register_restaurant(verified_token: dict[str, Any] | None):
    """
    Register a new restaurant with domain verification.
    """
    require_condition(verified_token, "Verified token is required")

    name = verified_token["name"]
    description = verified_token["description"]
    domain = verified_token["domain"]
    owner = verified_token["owner"]

    require_condition(name and description, "name and description are required")
    restaurant = create_restaurant(name, description, domain, owner)
    return created_response(serialize_restaurant_creation(restaurant))


@bp.patch("/<int:restaurant_id>")
@require_auth(["customer"])
@send_and_verify_domain_token
@require_restaurant_owner
def update_restaurant_profile(verified_token: dict[str, Any] | None, restaurant_id: int):
    """
    Update restaurant profile.
    """
    if verified_token:
        # Extract the claims from the secure token
        restaurant = find_restaurant_by_id(verified_token["restaurant_id"])
        name = verified_token["name"]
        description = verified_token["description"]
        domain = verified_token["domain"]
    else:
        # No token -> update restaurant with insecure data; DO NOT UPDATE DOMAIN THIS WAY!
        restaurant = find_restaurant_by_id(restaurant_id)
        name = get_param("name")
        description = get_param("description")
        # A domain with no token should be rejected by @domain_verification_required
        domain = None

    require_condition(name or description or domain, "name or description or domain is required")
    update_restaurant(restaurant, name, description, domain)

    return success_response(serialize_restaurant(restaurant))
