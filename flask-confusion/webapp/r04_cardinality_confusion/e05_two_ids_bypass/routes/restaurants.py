"""Restaurant Controller - delegates to restaurants_validators.py and restaurants_service.py.

All endpoints use consistent find_X_by_restaurant pattern for idiomatic ORM access.

v405 Migration: All mutation endpoints now require JSON bodies exclusively.
The @bp.before_request hook enforces this for POST/PATCH/PUT/DELETE methods.
"""

from flask import Blueprint

from ..auth.decorators import (
    require_auth,
    require_restaurant_manager,
    require_restaurant_owner,
    send_and_verify_domain_token,
)
from ..auth.middleware import require_json_for_mutations
from ..database.repository import (
    create_restaurant,
    create_restaurant_menu_item,
    find_all_restaurants,
    find_restaurant_by_id,
    find_restaurant_coupons,
    find_restaurant_menu_items,
    find_restaurant_orders,
    find_restaurant_refunds,
    find_restaurant_users,
    find_restaurant_refund_by_order_id,
    update_restaurant,
    update_restaurant_menu_item,
)
from ..database.services import issue_order_refund
from ..utils import created_response, not_found_response, success_response
from .restaurants_validators import (
    require_condition,
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
)

bp = Blueprint("restaurants", __name__, url_prefix="/restaurants")


@bp.before_request
def _require_json_for_mutations():
    require_json_for_mutations()


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
    restaurant = find_restaurant_by_id(restaurant_id)
    return (
        success_response(serialize_restaurant(restaurant)) if restaurant else not_found_response()
    )


# ============================================================
# RESTAURANT MANAGEMENT ENDPOINTS (API KEY AUTH)
# ============================================================
@bp.get("/<int:restaurant_id>/users")
@require_auth(["restaurant_api_key"])
@require_restaurant_manager
def list_users():
    """List all users associated with this restaurant."""
    users = find_restaurant_users()
    return success_response(serialize_users(users))


@bp.get("/<int:restaurant_id>/coupons")
@require_auth(["restaurant_api_key"])
@require_restaurant_manager
def list_coupons():
    """Lists all coupons for this restaurant."""
    coupons = find_restaurant_coupons()
    return success_response(serialize_coupons(coupons))


@bp.get("/<int:restaurant_id>/menu")
@require_auth(["restaurant_api_key"])
@require_restaurant_manager
def list_menu_items():
    """Lists all menu items for this restaurant."""
    menu_items = find_restaurant_menu_items()
    return success_response(serialize_menu_items(menu_items))


@bp.patch("/<int:restaurant_id>/menu/<int:item_id>")
@require_auth(["restaurant_api_key"])
@require_restaurant_manager
def update_menu_item(item_id: int):
    """Update a menu item."""
    name, price, available = validate_menu_item_fields(require_any=True)
    menu_item = update_restaurant_menu_item(item_id, name, price, available)

    return success_response(serialize_menu_item(menu_item)) if menu_item else not_found_response()


@bp.get("/<int:restaurant_id>/orders")
@require_auth(["restaurant_api_key"])
@require_restaurant_manager
def list_orders():
    """Lists all orders for this restaurant."""
    orders = find_restaurant_orders()
    return success_response(serialize_orders(orders))


@bp.get("/<int:restaurant_id>/refunds")
@require_auth(["restaurant_api_key"])
@require_restaurant_manager
def list_refunds():
    """Lists all refunds for this restaurant's orders."""
    refunds = find_restaurant_refunds()
    return success_response(serialize_refunds(refunds))


@bp.get("/<int:restaurant_id>/orders/<int:order_id>")
@require_auth(["restaurant_api_key"])
@require_restaurant_manager
def get_order(order_id: int):
    """Get a single order for this restaurant."""
    orders = find_restaurant_orders([order_id])
    return success_response(serialize_order(orders[0])) if orders else not_found_response()


@bp.get("/<int:restaurant_id>/orders/<int:order_id>/refund")
@require_auth(["restaurant_api_key"])
@require_restaurant_manager
def get_refund(order_id: int):
    """Get refund for a specific order."""
    refund = find_restaurant_refund_by_order_id(order_id)
    return success_response(serialize_refund(refund)) if refund else not_found_response()


@bp.post("/<int:restaurant_id>/refunds")
@require_auth(["restaurant_api_key"])
@require_restaurant_manager
def batch_refund():
    """Initiate batch refunds for multiple orders."""
    order_ids, reason = validate_batch_refund_request()

    # Filter orders to only those belonging to this restaurant
    orders = find_restaurant_orders(order_ids)
    require_condition(orders, "Orders not found for this restaurant")
    require_condition(len(orders) == len(order_ids), "All orders must belong to this restaurant")

    results = [issue_order_refund(oid, reason, auto_approved=True) for oid in order_ids]
    return success_response(serialize_batch_refund_result(results))


@bp.post("/<int:restaurant_id>/menu")
@require_auth(["restaurant_api_key"])
@require_restaurant_manager
def create_new_menu_item():
    """Create a new menu item for this restaurant."""
    name, price, available = validate_menu_item_fields(require_name=True, require_price=True)
    menu_item = create_restaurant_menu_item(name, price, available)
    return created_response(serialize_menu_item(menu_item))


# ============================================================
# RESTAURANT REGISTRATION/PROFILE ENDPOINTS (CUSTOMER AUTH)
# ============================================================
@bp.post("")
@require_auth(["customer"])
@send_and_verify_domain_token
def register_restaurant(name, description, domain, owner):
    """Register a new restaurant with domain verification."""
    require_condition(name and description and domain and owner, "missing required fields")

    restaurant = create_restaurant(name=name, description=description, domain=domain, owner=owner)
    return created_response(serialize_restaurant_creation(restaurant))


@bp.patch("/<int:restaurant_id>")
@require_auth(["customer"])
@require_restaurant_owner
@send_and_verify_domain_token
def update_restaurant_profile(name, description, domain):
    """Update restaurant profile."""
    require_condition(name or description or domain, "name or description or domain is required")

    restaurant = update_restaurant(name=name, description=description, domain=domain)
    return success_response(serialize_restaurant(restaurant))
