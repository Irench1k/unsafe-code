import logging
from decimal import Decimal

from flask import Blueprint, g, jsonify, request

from ..auth.decorators import protect_refunds, require_auth, verify_order_access
from ..database.repository import find_all_orders, get_refund_by_order_id
from ..database.services import (
    create_refund,
    get_user_orders,
    process_refund,
    serialize_orders,
    serialize_refund,
    update_order_refund_status,
)
from ..errors import CheekyApiError
from ..utils import get_request_parameter, normalize_order_id, parse_as_decimal

logger = logging.getLogger(__name__)
bp = Blueprint("orders", __name__, url_prefix="/orders")


@bp.get("")
@require_auth(["customer", "restaurant_api_key"])
def list_orders():
    """Customers can list their own orders, restaurant managers can list ALL of them."""
    orders = find_all_orders() if g.get("manager_request") else get_user_orders(g.email)
    return jsonify(serialize_orders(orders))


@bp.post("/<order_id>/refund")
@require_auth(["customer"])
@verify_order_access
@protect_refunds
def refund_order(order_id):
    """Refunds an order."""
    normalized_order_id = g.order.order_id

    if g.order.user_id != g.email:
        raise CheekyApiError("Order does not belong to user")

    if getattr(g.order, "refunded", False):
        raise CheekyApiError("Order has already been refunded")

    if get_refund_by_order_id(normalized_order_id):
        raise CheekyApiError("Refund already exists for this order")

    reason = get_request_parameter("reason") or ""
    refund_amount_entered = parse_as_decimal(get_request_parameter("amount"))
    refund_amount = refund_amount_entered or Decimal("0.2") * g.order.total

    refund = create_refund(
        order_id=normalized_order_id,
        amount=refund_amount,
        reason=reason,
        auto_approved=g.refund_is_auto_approved,
    )

    process_refund(refund, g.email)
    return jsonify(serialize_refund(refund)), 200


@bp.patch("/<order_id>/refund/status")
@require_auth(["restaurant_api_key"])
def update_refund_status(order_id):
    """Updates the status of a refund."""
    normalized_order_id = normalize_order_id(order_id)
    if not normalized_order_id:
        raise CheekyApiError("Invalid order ID")

    status = request.form.get("status")
    if not status or status not in ["approved", "rejected"]:
        raise CheekyApiError("Status is missing or invalid")

    refund = update_order_refund_status(normalized_order_id, status)
    if not refund:
        raise CheekyApiError("Refund not found")
    return jsonify(serialize_refund(refund)), 200


@bp.get("/<order_id>/refund/status")
@require_auth(["customer"])
@verify_order_access
def get_refund_status(order_id):
    """Gets the status of a refund."""
    normalized_order_id = normalize_order_id(order_id)
    if not normalized_order_id:
        raise CheekyApiError("Invalid order ID")

    if normalized_order_id != g.order.order_id:
        raise CheekyApiError("Order mismatch detected")

    refund = get_refund_by_order_id(normalized_order_id)
    if not refund:
        raise CheekyApiError("Refund not found")

    return jsonify(serialize_refund(refund)), 200
