"""Restaurant Controller - delegates to restaurants_validators.py and restaurants_service.py.

All endpoints use consistent find_X_by_restaurant pattern for idiomatic ORM access.
"""

from typing import Any

from flask import Blueprint

from ..auth.decorators import (
    require_auth,
    require_restaurant_manager,
    require_restaurant_owner,
    send_and_verify_domain_token,
)
from ..database.repository import (
    find_all_restaurants,
    find_coupons_by_restaurant,
    find_menu_item_by_restaurant,
    find_menu_items_by_restaurant,
    find_orders_by_restaurant,
    find_refunds_by_restaurant,
    find_users_by_restaurant,
    get_refund_by_order_id,
)
from ..database.services import issue_order_refund
from ..utils import created_response, require_condition, success_response
from . import restaurants_service
from .restaurants_validators import (
    get_trusted_restaurant,
    serialize_batch_refund_result,
    serialize_coupons,
    serialize_menu_item,
    serialize_menu_items,
    serialize_order,
    serialize_orders,
    serialize_refund,
    serialize_refunds,
    serialize_restaurant,
    serialize_restaurant_creation,
    serialize_restaurants,
    serialize_users,
    validate_batch_refund_request,
    validate_menu_item_fields,
    validate_restaurant_registration,
    validate_restaurant_update,
)

bp = Blueprint("restaurants", __name__, url_prefix="/restaurants")


# ============================================================
# PUBLIC RESTAURANT ENDPOINTS
# ============================================================
@bp.get("")
def list_restaurants():
    """Lists all restaurants in the system."""
    restaurants = find_all_restaurants()
    return success_response(serialize_restaurants(restaurants))


@bp.get("/<int:restaurant_id>/")
def get_restaurant(restaurant_id: int):
    """Get a restaurant."""
    restaurant = get_trusted_restaurant(restaurant_id)
    return success_response(serialize_restaurant(restaurant))


# ============================================================
# RESTAURANT MANAGEMENT ENDPOINTS (API KEY AUTH)
# ============================================================
@bp.get("/<int:restaurant_id>/users")
@require_auth(["restaurant_api_key"])
@require_restaurant_manager
def list_users(restaurant_id: int):
    """List all users associated with this restaurant."""
    users = find_users_by_restaurant(restaurant_id)
    return success_response(serialize_users(users))


@bp.get("/<int:restaurant_id>/coupons")
@require_auth(["restaurant_api_key"])
@require_restaurant_manager
def list_coupons(restaurant_id: int):
    """Lists all coupons for this restaurant."""
    coupons = find_coupons_by_restaurant(restaurant_id)
    return success_response(serialize_coupons(coupons))


@bp.get("/<int:restaurant_id>/menu")
@require_auth(["restaurant_api_key"])
@require_restaurant_manager
def list_menu_items(restaurant_id: int):
    """Lists all menu items for this restaurant."""
    menu_items = find_menu_items_by_restaurant(restaurant_id)
    return success_response(serialize_menu_items(menu_items))


@bp.patch("/<int:restaurant_id>/menu/<int:item_id>")
@require_auth(["restaurant_api_key"])
@require_restaurant_manager
def update_menu_item(restaurant_id: int, item_id: int):
    """Update a menu item."""
    menu_item = find_menu_item_by_restaurant(restaurant_id, item_id)
    require_condition(menu_item, f"Menu item {item_id} not found")

    fields = validate_menu_item_fields(require_any=True)

    menu_item = restaurants_service.apply_menu_item_changes(menu_item, fields)
    return success_response(serialize_menu_item(menu_item))


@bp.get("/<int:restaurant_id>/orders")
@require_auth(["restaurant_api_key"])
@require_restaurant_manager
def list_orders(restaurant_id: int):
    """Lists all orders for this restaurant."""
    orders = find_orders_by_restaurant(restaurant_id)
    return success_response(serialize_orders(orders))


@bp.get("/<int:restaurant_id>/refunds")
@require_auth(["restaurant_api_key"])
@require_restaurant_manager
def list_refunds(restaurant_id: int):
    """Lists all refunds for this restaurant's orders."""
    refunds = find_refunds_by_restaurant(restaurant_id)
    return success_response(serialize_refunds(refunds))


@bp.get("/<int:restaurant_id>/orders/<int:order_id>")
@require_auth(["restaurant_api_key"])
@require_restaurant_manager
def get_order(restaurant_id: int, order_id: int):
    """Get a single order for this restaurant."""
    orders = find_orders_by_restaurant(restaurant_id, [order_id])
    require_condition(orders, "Order not found for this restaurant")
    return success_response(serialize_order(orders[0]))


@bp.get("/<int:restaurant_id>/orders/<int:order_id>/refund")
@require_auth(["restaurant_api_key"])
@require_restaurant_manager
def get_refund(restaurant_id: int, order_id: int):
    """Get refund for a specific order."""
    orders = find_orders_by_restaurant(restaurant_id, [order_id])
    require_condition(orders, "Order not found for this restaurant")

    refund = get_refund_by_order_id(order_id)
    require_condition(refund, "No refund for this order")
    return success_response(serialize_refund(refund))


# @unsafe {
#     "vuln_id": "v404",
#     "severity": "critical",
#     "category": "cardinality-confusion",
#     "description": "Authorization check filters orders to restaurant, but handler processes original unfiltered order_ids list",
#     "cwe": "CWE-863"
# }
@bp.post("/<int:restaurant_id>/refunds")
@require_auth(["restaurant_api_key"])
@require_restaurant_manager
def batch_refund(restaurant_id: int):
    """Initiate batch refunds for multiple orders."""
    order_ids, reason = validate_batch_refund_request()

    orders = find_orders_by_restaurant(restaurant_id, order_ids)
    require_condition(orders, "Orders not found for this restaurant")

    results = [issue_order_refund(oid, reason, auto_approved=True) for oid in order_ids]
    return success_response(serialize_batch_refund_result(results))


@bp.post("/<int:restaurant_id>/menu")
@require_auth(["restaurant_api_key"])
@require_restaurant_manager
def create_menu_item(restaurant_id: int):
    """Create a new menu item for this restaurant."""
    fields = validate_menu_item_fields(require_name=True, require_price=True)
    menu_item = restaurants_service.create_menu_item_for_restaurant(restaurant_id, fields)
    return created_response(serialize_menu_item(menu_item))


# ============================================================
# RESTAURANT REGISTRATION/PROFILE ENDPOINTS (CUSTOMER AUTH)
# ============================================================
@bp.post("")
@require_auth(["customer"])
@send_and_verify_domain_token
def register_restaurant(verified_token: dict[str, Any] | None):
    """Register a new restaurant with domain verification."""
    registration = validate_restaurant_registration(verified_token)
    restaurant = restaurants_service.create_restaurant(
        name=registration["name"],
        description=registration["description"],
        domain=registration["domain"],
        owner=registration["owner"],
    )
    return created_response(serialize_restaurant_creation(restaurant))


@bp.patch("/<int:restaurant_id>")
@require_auth(["customer"])
@require_restaurant_owner
@send_and_verify_domain_token
def update_restaurant_profile(verified_token: dict[str, Any] | None, restaurant_id: int):
    """Update restaurant profile."""
    update_data = validate_restaurant_update(verified_token)
    restaurant = get_trusted_restaurant(restaurant_id)

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

    return success_response(serialize_restaurant(restaurant))
