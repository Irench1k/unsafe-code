import logging
from decimal import Decimal

from flask import Blueprint, g, jsonify, request

from ..auth.decorators import protect_refunds, require_auth, verify_order_access
from ..auth.helpers import has_access_to_order
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
    refund_user,
    serialize_order,
    serialize_orders,
    serialize_refund,
    update_order_refund_status,
)
from ..errors import CheekyApiError
from ..utils import get_request_parameter, parse_as_decimal

logger = logging.getLogger(__name__)
bp = Blueprint("orders", __name__, url_prefix="/orders")


def _parse_order_id(raw_order_id: str) -> int:
    try:
        order_id = int(raw_order_id)
    except (TypeError, ValueError):
        raise CheekyApiError("Invalid order_id") from None
    if order_id <= 0:
        raise CheekyApiError("Invalid order_id")
    return order_id


@bp.get("")
@require_auth(["customer", "restaurant_api_key"])
def list_orders():
    """Customers can list their own orders, restaurant managers can list ALL of them."""
    if g.get("manager_request") and g.get("restaurant_id"):
        orders = find_orders_by_restaurant(g.restaurant_id)
    elif g.get("customer_request") and g.get("user_id"):
        orders = get_user_orders(g.user_id)
    else:
        raise CheekyApiError("Something went wrong")

    return jsonify(serialize_orders(orders))


@bp.post("/<order_id>/refund")
@require_auth(["customer"])
@verify_order_access
@protect_refunds
def refund_order(order_id):
    """Initiates a refund for a customer's order. Customer-only."""
    order_id_int = _parse_order_id(order_id)

    # Authorization check: order must belong to the user
    if g.order.user_id != g.user_id:
        raise CheekyApiError("Order does not belong to user")

    # Integrity check: order must be delivered, not refunded or cancelled
    # (the orders that are not delivered yet can only be cancelled not refunded)
    if g.order.status != OrderStatus.delivered:
        raise CheekyApiError("Order cannot be refunded")

    # Integrity check: there should NOT be other refunds for this order already
    if get_refund_by_order_id(order_id_int):
        raise CheekyApiError("Refund already exists for this order")

    reason = get_request_parameter("reason") or ""
    refund_amount_entered = parse_as_decimal(get_request_parameter("amount"))
    refund_amount = refund_amount_entered or Decimal("0.2") * g.order.total

    refund = create_refund(
        order_id=order_id_int,
        amount=refund_amount,
        reason=reason,
        auto_approved=g.refund_is_auto_approved,
    )

    process_refund(refund, g.user_id)
    return jsonify(serialize_refund(refund)), 200


@bp.patch("/<order_id>/refund/status")
@require_auth(["restaurant_api_key"])
def update_refund_status(order_id):
    """Approves or rejects a refund. Restaurant-only."""
    order_id_int = _parse_order_id(order_id)
    status = request.form.get("status")
    if not status or status not in ["approved", "rejected"]:
        raise CheekyApiError("Status is missing or invalid")

    if not has_access_to_order(order_id_int):
        raise CheekyApiError("Order does not belong to restaurant")

    refund = update_order_refund_status(order_id_int, status)
    if not refund:
        raise CheekyApiError("Refund not found")
    return jsonify(serialize_refund(refund)), 200


@bp.get("/<order_id>/refund/status")
@require_auth(["customer"])
def get_refund_status(order_id):
    """Gets the status of a refund. Customer-only."""
    order_id_int = _parse_order_id(order_id)
    order = find_order_by_id(order_id_int)
    if not order:
        raise CheekyApiError("Order not found")

    # Authorization check: order must belong to the user
    if order.user_id != g.user_id:
        raise CheekyApiError("Order does not belong to user")

    refund = get_refund_by_order_id(order_id_int)
    if not refund:
        raise CheekyApiError("Refund not found")

    return jsonify(serialize_refund(refund)), 200


@bp.patch("/<order_id>/status")
@require_auth(["restaurant_api_key", "customer"])
def update_order_status(order_id):
    """
    Update order status. Available to both customers and restaurant managers.

    Order status can be changed only from "created".
    Customers and restaurant managers have different rules.

    Customers:
    - can change order status to cancelled
    - only if order has not been delivered yet

    Restaurants:
    - can change order status to delivered or cancelled
    - only if order has been created and not delivered yet
    """
    order_id_int = _parse_order_id(order_id)
    try:
        status = OrderStatus(request.form.get("status"))
    except ValueError:
        raise CheekyApiError("Status is missing or invalid")
    if status not in [OrderStatus.delivered, OrderStatus.cancelled]:
        raise CheekyApiError(f"Status is invalid: got '{status.value}'")

    order = find_order_by_id(order_id_int)
    if not order:
        raise CheekyApiError("Order not found")

    # Authorization check: order must belong to the user or restaurant
    if g.get("user_id"):
        if order.user_id != g.user_id:
            raise CheekyApiError("Order does not belong to user")
        # Integrity check: customers can only cancel orders
        if status != OrderStatus.cancelled:
            raise CheekyApiError(f"Order can only be cancelled: got status '{status.value}'")
    else:
        if order.restaurant_id != g.restaurant_id:
            raise CheekyApiError("Order does not belong to restaurant")
        # Integrity check: restaurants can only deliver or cancel orders
        if status not in [OrderStatus.delivered, OrderStatus.cancelled]:
            raise CheekyApiError("Order can only be delivered or cancelled")

    # Integrity check: order status can be changed only from "created"
    if order.status != OrderStatus.created:
        raise CheekyApiError("Order status can be changed only from 'created'")

    order.status = status
    save_order(order)
    if status == OrderStatus.cancelled:
        refund_user(order.user_id, order.total)
    return jsonify(serialize_order(order)), 200
