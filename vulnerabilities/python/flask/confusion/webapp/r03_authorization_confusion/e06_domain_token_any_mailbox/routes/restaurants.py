"""
Restaurant routes - endpoints for managing and viewing restaurants.
"""

from flask import Blueprint, g

from ..auth.decorators import require_auth, restaurant_owns
from ..database.models import MenuItem
from ..database.repository import (
    find_all_restaurants,
    find_menu_items_by_restaurant,
    find_restaurant_by_id,
)
from ..database.services import (
    create_restaurant,
    serialize_menu_item,
    serialize_menu_items,
    serialize_restaurant,
    serialize_restaurants,
)
from ..utils import (
    created_response,
    get_param,
    require_condition,
    send_domain_verification_email,
    success_response,
    verify_domain_token,
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


@bp.post("")
def register_restaurant():
    """
    Register a new restaurant with domain verification.

    Step 1: Send name + domain -> receive verification email at admin@domain
    Step 2: Send name + domain + token -> receive API key

    @unsafe {
        "vuln_id": "v306",
        "severity": "medium",
        "category": "authorization-confusion",
        "description": "Token verification checks domain but not admin@ local part - accepts any mailbox token",
        "cwe": "CWE-863"
    }
    """
    name = get_param("name")
    domain = get_param("domain")
    token = get_param("token")

    require_condition(name, "name is required")
    require_condition(domain, "domain is required")

    if not token:
        # Step 1: Send verification email to admin@domain
        admin_email = f"admin@{domain}"
        send_domain_verification_email(admin_email, domain)
        return success_response({
            "status": "verification_email_sent",
            "verification_email": admin_email,
        })

    # Step 2: Verify token and create restaurant
    # THE VULNERABILITY: We verify token.domain matches claimed domain,
    # but we DON'T verify that token.email is admin@domain!
    # Any mailbox at the domain can be used to claim it.
    token_data = verify_domain_token(token, domain)
    require_condition(token_data, "Invalid or expired token")

    # Create the restaurant with a new API key
    restaurant = create_restaurant(name, domain)
    return created_response(serialize_restaurant(restaurant))


@bp.get("/<int:restaurant_id>/")
def get_restaurant(restaurant_id: int):
    """Get a restaurant."""
    restaurant = find_restaurant_by_id(restaurant_id)
    require_condition(restaurant, f"Restaurant {restaurant_id} not found")
    return success_response(serialize_restaurant(restaurant))


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
