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
    orders = find_all_orders() if g.get("manager_request") else get_user_orders(g.user.id)
    return jsonify(serialize_orders(orders))


@bp.post("/<order_id>/refund")
@require_auth(["customer"])
@verify_order_access
@protect_refunds
def refund_order(order_id):
    """Refunds an order."""
    order_id_int = _parse_order_id(order_id)
    reason = get_request_parameter("reason") or ""
    refund_amount_entered = parse_as_decimal(get_request_parameter("amount"))
    refund_amount = refund_amount_entered or Decimal("0.2") * g.order.total

    refund = create_refund(
        order_id=order_id_int,
        amount=refund_amount,
        reason=reason,
        auto_approved=g.refund_is_auto_approved,
    )

    process_refund(refund, g.user.id)
    return jsonify(serialize_refund(refund)), 200


@bp.patch("/<order_id>/refund/status")
@require_auth(["restaurant_api_key"])
def update_refund_status(order_id):
    """Updates the status of a refund."""
    order_id_int = _parse_order_id(order_id)
    status = request.form.get("status")
    if not status or status not in ["approved", "rejected"]:
        raise CheekyApiError("Status is missing or invalid")

    refund = update_order_refund_status(order_id_int, status)
    if not refund:
        raise CheekyApiError("Refund not found")
    return jsonify(serialize_refund(refund)), 200


@bp.get("/<order_id>/refund/status")
@require_auth(["customer"])
def get_refund_status(order_id):
    """Gets the status of a refund."""
    order_id_int = _parse_order_id(order_id)
    refund = get_refund_by_order_id(order_id_int)
    if not refund:
        raise CheekyApiError("Refund not found")

    return jsonify(serialize_refund(refund)), 200
