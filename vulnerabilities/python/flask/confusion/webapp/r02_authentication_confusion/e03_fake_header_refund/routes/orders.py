from decimal import Decimal

from flask import Blueprint, g, jsonify, request

from ..auth.decorators import (
    protect_refunds,
    verify_order_access,
)
from ..auth.helpers import authenticate_customer, validate_api_key
from ..database.models import Refund
from ..database.repository import (
    find_all_orders,
    get_refund_by_order_id,
    save_refund,
)
from ..database.services import (
    create_refund,
    get_user_orders,
    process_refund,
    refund_user,
    serialize_orders,
    serialize_refund,
    update_order_refund_status,
)
from ..errors import CheekyApiError
from ..utils import get_request_parameter, parse_as_decimal

bp = Blueprint("orders", __name__, url_prefix="/orders")


# Protect all orders to reduce number of decorators
@bp.before_request
def require_customer_or_restaurant():
    """Requires the user to be a customer or a restaurant manager."""
    if not authenticate_customer() and not validate_api_key():
        raise CheekyApiError("Unauthorized")


def authenticated_with(role: str) -> bool:
    """Checks if the user is authenticated with the given role."""
    if role == "restaurant":
        return "x-api-key" in request.headers
    elif role == "customer":
        return getattr(g, "email", None) is not None
    else:
        raise CheekyApiError("Invalid role")


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
@verify_order_access
@protect_refunds
def refund_order(order_id):
    """Refunds an order."""
    reason = get_request_parameter("reason") or ""
    refund_amount_entered = parse_as_decimal(get_request_parameter("amount"))
    refund_amount = refund_amount_entered or Decimal("0.2") * g.order.total

    # TODO: The new approach
    refund = create_refund(
        order_id=order_id,
        amount=refund_amount,
        reason=reason,
        auto_approved=g.refund_is_auto_approved,
    )

    process_refund(refund, g.email)
    return jsonify(serialize_refund(refund)), 200

    # status = "auto_approved" if g.refund_is_auto_approved else "pending"

    # refund = Refund(
    #     order_id=order_id,
    #     amount=refund_amount,
    #     reason=reason,
    #     status=status,
    #     auto_approved=g.refund_is_auto_approved,
    # )

    # if g.refund_is_auto_approved:
    #     refund_user(g.email, refund_amount)

    # save_refund(refund)
    # return jsonify(refund.model_dump(mode="json")), 200


@bp.patch("/<order_id>/refund/status")
def update_refund_status(order_id):
    """Updates the status of a refund."""
    print(f"Updating refund status for order {order_id}")
    if not authenticated_with("restaurant"):
        raise CheekyApiError("Unauthorized")

    status = request.form.get("status")
    if not status or status not in ["approved", "rejected"]:
        raise CheekyApiError("Status is missing or invalid")

    refund = update_order_refund_status(order_id, status)
    if not refund:
        raise CheekyApiError("Refund not found")
    return jsonify(serialize_refund(refund)), 200


@bp.get("/<order_id>/refund/status")
def get_refund_status(order_id):
    """Gets the status of a refund."""
    if not authenticated_with("customer"):
        raise CheekyApiError("Unauthorized")

    refund = get_refund_by_order_id(order_id)
    if not refund:
        raise CheekyApiError("Refund not found")

    return jsonify(serialize_refund(refund)), 200
