"""Restaurant Controller - delegates to restaurants_validators.py and restaurants_service.py."""

from typing import Any

from flask import Blueprint, g

from ..auth.decorators import (
    require_auth,
    require_restaurant_manager,
    require_restaurant_owner,
    restaurant_owns,
    send_and_verify_domain_token,
)
from ..database.models import MenuItem
from ..database.repository import (
    find_all_restaurants,
    find_coupons_by_restaurant,
    find_menu_items_by_restaurant,
    find_restaurant_users,
)
from ..utils import created_response, require_condition, success_response
from . import restaurants_service, restaurants_validators

bp = Blueprint("restaurants", __name__, url_prefix="/restaurants")


# ============================================================
# PUBLIC RESTAURANT ENDPOINTS
# ============================================================
@bp.get("")
def list_restaurants():
    """Lists all restaurants in the system."""
    restaurants = find_all_restaurants()
    return success_response(restaurants_validators.serialize_restaurants(restaurants))


@bp.get("/<int:restaurant_id>/")
def get_restaurant(restaurant_id: int):
    """Get a restaurant."""
    restaurant = restaurants_validators.get_trusted_restaurant(restaurant_id)
    return success_response(restaurants_validators.serialize_restaurant(restaurant))


@bp.get("/<int:restaurant_id>/menu")
def list_menu_items(restaurant_id: int):
    """Lists all menu items for a restaurant."""
    restaurants_validators.get_trusted_restaurant(restaurant_id)
    menu_items = find_menu_items_by_restaurant(restaurant_id)
    return success_response(restaurants_validators.serialize_menu_items(menu_items))


# ============================================================
# RESTAURANT MANAGEMENT ENDPOINTS (API KEY AUTH)
# ============================================================
@bp.get("/<int:restaurant_id>/users")
@require_auth(["restaurant_api_key"])
@require_restaurant_manager
def list_users(restaurant_id: int):
    """List all users in the system with a matching email address."""
    users = find_restaurant_users(restaurant_id)
    return success_response(restaurants_validators.serialize_restaurant_users(users))


@bp.get("/<int:restaurant_id>/coupons")
@require_auth(["restaurant_api_key"])
@require_restaurant_manager
def list_coupons(restaurant_id: int):
    """Lists all coupons for a restaurant."""
    coupons = find_coupons_by_restaurant(restaurant_id)
    return success_response(restaurants_validators.serialize_coupons(coupons))


@bp.post("/<int:restaurant_id>/menu")
@require_auth(["restaurant_api_key"])
@require_restaurant_manager
def create_menu_item(restaurant_id: int):
    """Create a new menu item for the authenticated restaurant."""
    require_condition(
        getattr(g, "restaurant_id", None) == restaurant_id,
        "Unauthorized",
    )
    fields = restaurants_validators.validate_menu_item_fields(require_name=True, require_price=True)
    menu_item = restaurants_service.create_menu_item_for_restaurant(restaurant_id, fields)
    return created_response(restaurants_validators.serialize_menu_item(menu_item))


@bp.patch("/<int:restaurant_id>/menu/<int:item_id>")
@require_auth(["restaurant_api_key"])
@require_restaurant_manager
@restaurant_owns(MenuItem, "item_id")
def update_menu_item(restaurant_id: int, item_id: int):
    """Update a menu item."""
    menu_item = restaurants_validators.validate_menu_item_exists(item_id)
    fields = restaurants_validators.validate_menu_item_fields(require_any=True)
    menu_item = restaurants_service.apply_menu_item_changes(menu_item, fields)
    return success_response(restaurants_validators.serialize_menu_item(menu_item))


# ============================================================
# RESTAURANT REGISTRATION/PROFILE ENDPOINTS (CUSTOMER AUTH)
# ============================================================
@bp.post("")
@require_auth(["customer"])
@send_and_verify_domain_token
def register_restaurant(verified_token: dict[str, Any] | None):
    """Register a new restaurant with domain verification."""
    registration = restaurants_validators.validate_restaurant_registration(verified_token)
    restaurant = restaurants_service.create_restaurant(
        name=registration["name"],
        description=registration["description"],
        domain=registration["domain"],
        owner=registration["owner"],
    )
    return created_response(restaurants_validators.serialize_restaurant_creation(restaurant))


@bp.patch("/<int:restaurant_id>")
@require_auth(["customer"])
@require_restaurant_owner
@send_and_verify_domain_token
def update_restaurant_profile(verified_token: dict[str, Any] | None, restaurant_id: int):
    """Update restaurant profile."""
    update_data = restaurants_validators.validate_restaurant_update(verified_token)
    restaurant = restaurants_validators.get_trusted_restaurant(restaurant_id)

    require_condition(
        update_data["name"] or update_data["description"] or update_data["domain"],
        "name or description or domain is required",
    )

    restaurants_service.update_restaurant(
        restaurant,
        name=update_data["name"],
        description=update_data["description"],
        domain=update_data["domain"],
    )

    return success_response(restaurants_validators.serialize_restaurant(restaurant))


# ============================================================
# BATCH OPERATIONS
# ============================================================
@bp.post("/<int:restaurant_id>/refunds")
@require_auth(["restaurant_api_key"])
@require_restaurant_manager
def batch_refund(restaurant_id: int):
    """
    Initiate batch refunds for multiple orders.

    Restaurant managers can proactively refund orders before customers complain,
    useful for handling quality issues, delivery problems, or promotional goodwill.

    Request body: { "order_ids": [1, 2, 3], "reason": "Quality issue" }
    """
    data = restaurants_validators.validate_batch_refund_request()
    processed_ids, skipped_ids = restaurants_service.process_batch_refund(
        restaurant_id=restaurant_id,
        order_ids=data["order_ids"],
        reason=data["reason"],
    )
    return success_response(
        restaurants_validators.serialize_batch_refund_result(processed_ids, skipped_ids)
    )
