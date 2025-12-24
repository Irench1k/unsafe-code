from decimal import Decimal

from flask import Blueprint, g, jsonify

from ..auth.decorators import (
    customer_authentication_required,
    protect_refunds,
    verify_order_access,
)
from ..auth.helpers import authenticate_customer, validate_api_key
from ..database.repository import find_all_orders
from ..database.services import (
    create_refund,
    get_user_orders,
    process_refund,
    serialize_orders,
    serialize_refund,
)
from ..errors import CheekyApiError
from ..utils import get_request_parameter, parse_as_decimal

bp = Blueprint("orders", __name__, url_prefix="/orders")


@bp.get("")
def list_orders():
    """Customers can list their own orders, restaurant managers can list ALL of them."""

    # Customer -> List their own orders
    if authenticate_customer():
        orders = get_user_orders(g.email)
        return jsonify(serialize_orders(orders))

    # Restaurant manager -> List all orders
    if validate_api_key():
        orders = find_all_orders()
        return jsonify(serialize_orders(orders))

    raise CheekyApiError("Unauthorized")


@bp.post("/<order_id>/refund")
@customer_authentication_required
@verify_order_access
@protect_refunds
def refund_order(order_id):
    """Refunds an order."""
    reason = get_request_parameter("reason") or ""
    refund_amount_entered = parse_as_decimal(get_request_parameter("amount"))
    refund_amount = refund_amount_entered or Decimal("0.2") * g.order.total

    refund = create_refund(
        order_id=order_id,
        amount=refund_amount,
        reason=reason,
        auto_approved=g.refund_is_auto_approved,
    )

    process_refund(refund, g.email)
    return jsonify(serialize_refund(refund)), 200
