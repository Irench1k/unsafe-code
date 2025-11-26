import logging

from flask import Blueprint, g

from ..auth.decorators import protect_refunds, require_auth, verify_order_access
from ..config import OrderConfig
from ..database.models import OrderStatus
from ..database.repository import (
    find_order_by_id,
    find_orders_by_restaurant,
    get_refund_by_order_id,
    save_order,
)
from ..database.services import (
    create_refund,
    get_user_orders,
    process_refund,
    serialize_order,
    serialize_orders,
    serialize_refund,
    update_order_refund_status,
)
from ..errors import CheekyApiError
from ..utils import (
    bind_to_restaurant,
    get_decimal_param,
    get_param,
    require_condition,
    require_ownership,
    success_response,
)

logger = logging.getLogger(__name__)
bp = Blueprint("orders", __name__, url_prefix="/orders")


@bp.get("")
@require_auth(["customer", "restaurant_api_key"])
def list_orders():
    """
    Customers can list their own orders, restaurant managers can list ALL of them.

    @unsafe {
        "vuln_id": "v304",
        "severity": "high",
        "category": "authorization-confusion",
        "description": "Decorator implicitly trusts g.restaurant_id from API key, but bind_to_restaurant() overrides with body params",
        "cwe": "CWE-863"
    }
    """
    if g.get("manager_request") and g.get("restaurant_id"):
        # Use bind_to_restaurant() to auto-detect restaurant ID from any container
        # This is Sandy's new helper that checks query, form, AND JSON body
        # The vulnerability: decorator trusts API key's restaurant_id,
        # but we override it here with body params!
        bound_restaurant_id = bind_to_restaurant() or g.restaurant_id
        orders = find_orders_by_restaurant(bound_restaurant_id)
    elif g.get("customer_request") and g.get("user_id"):
        orders = get_user_orders(g.user_id)
    else:
        raise CheekyApiError("Something went wrong")

    return success_response(serialize_orders(orders))


@bp.post("/<int:order_id>/refund")
@require_auth(["customer"])
@verify_order_access
@protect_refunds
def refund_order(order_id: int):
    """Initiates a refund for a customer's order. Customer-only."""
    # Parse inputs
    reason = get_param("reason") or ""
    refund_amount = get_decimal_param(
        "amount", OrderConfig.DEFAULT_REFUND_PERCENTAGE * g.order.total
    )

    # Integrity check: order must not already be refunded
    require_condition(g.order.status != OrderStatus.refunded, "Order has already been refunded")

    # Integrity check: there should NOT be other refunds for this order
    require_condition(not get_refund_by_order_id(order_id), "Refund already exists for this order")

    # Create and save refund
    refund = create_refund(
        order_id=order_id,
        amount=refund_amount,
        reason=reason,
        auto_approved=g.refund_is_auto_approved,
    )

    process_refund(refund, g.user_id)
    return success_response(serialize_refund(refund))


@bp.patch("/<int:order_id>/refund/status")
@require_auth(["restaurant_api_key"])
def update_refund_status(order_id: int):
    """Approves or rejects a refund. Restaurant-only."""
    # Parse inputs
    status = get_param("status")
    require_condition(status in ["approved", "rejected"], "Status is missing or invalid")

    # Fetch order
    order = find_order_by_id(order_id)
    require_condition(order, f"Order {order_id} not found")

    # Authorization check: order must belong to the restaurant
    require_ownership(order.restaurant_id, g.restaurant_id, "order")

    # Update refund status
    refund = update_order_refund_status(order_id, status)
    require_condition(refund, f"Refund {order_id} not found")
    return success_response(serialize_refund(refund))


@bp.get("/<int:order_id>/refund/status")
@require_auth(["customer"])
def get_refund_status(order_id: int):
    """Gets the status of a refund. Customer-only."""
    order = find_order_by_id(order_id)
    require_condition(order, f"Order {order_id} not found")

    # Authorization check: order must belong to the user
    require_ownership(order.user_id, g.user_id, "order")

    # Fetch refund
    refund = get_refund_by_order_id(order_id)
    require_condition(refund, f"Refund {order_id} not found")

    return success_response(serialize_refund(refund))


@bp.patch("/<int:order_id>/status")
@require_auth(["restaurant_api_key", "customer"])
def update_order_status(order_id: int):
    """
    Update order status. Available to both customers and restaurant managers.

    Sandy rewrote this to push authorization into the database query itself.
    The UPDATE only affects rows where restaurant_id matches the authenticated user.

    @unsafe {
        "vuln_id": "v305",
        "severity": "high",
        "category": "authorization-confusion",
        "description": "Handler returns order data even when update is rejected due to invalid state transition",
        "cwe": "CWE-863"
    }
    """
    status = get_param("status")
    require_condition(
        status in ["created", "delivered", "cancelled", "refunded"], "Status is missing or invalid"
    )

    # Load order first (before any authorization!)
    order = find_order_by_id(order_id)
    require_condition(order, f"Order {order_id} not found")

    # Idempotency check - guard against illegal transitions
    # The vulnerability: this check happens BEFORE authorization,
    # and we return the order data even on rejection!
    if order.status == OrderStatus(status):
        # Can't transition to same state - return the order anyway!
        return success_response({
            **serialize_order(order),
            "updated": False,
            "rejection_reason": f"Order is already in '{status}' state"
        })

    # Authorization would happen in the UPDATE query itself...
    # but we already leaked the order data above!

    # Integrity check: order status can be changed only from "created"
    require_condition(
        order.status == OrderStatus.created, "Order status can be changed only from 'created'"
    )

    # Update order status
    order.status = status
    save_order(order)
    return success_response(serialize_order(order))
