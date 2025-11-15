from decimal import Decimal

from flask import Blueprint, g, jsonify

from ..auth.decorators import (
    customer_authentication_required,
    protect_refunds,
    verify_order_access,
)
from ..auth.helpers import authenticate_customer, validate_api_key
from ..database.models import Refund
from ..database.repository import find_all_orders, save_refund
from ..database.services import get_user_orders, refund_user
from ..errors import CheekyApiError
from ..utils import get_request_parameter, parse_as_decimal

bp = Blueprint("orders", __name__, url_prefix="/orders")


@bp.get("")
def list_orders():
    """Customers can list their own orders, restaurant managers can list ALL of them."""

    # Customer -> List their own orders
    if authenticate_customer():
        orders = get_user_orders(g.email)
        return jsonify([order.model_dump(mode="json") for order in orders])

    # Restaurant manager -> List all orders
    if validate_api_key():
        orders = find_all_orders()
        return jsonify([order.model_dump(mode="json") for order in orders])

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

    status = "auto_approved" if g.refund_is_auto_approved else "pending"

    refund = Refund(
        order_id=order_id,
        amount=refund_amount,
        reason=reason,
        status=status,
        auto_approved=g.refund_is_auto_approved,
    )

    if g.refund_is_auto_approved:
        refund_user(g.email, refund_amount)

    save_refund(refund)
    return jsonify(refund.model_dump(mode="json")), 200
