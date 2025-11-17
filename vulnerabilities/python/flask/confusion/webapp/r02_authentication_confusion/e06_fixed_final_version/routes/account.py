from flask import Blueprint, g, jsonify, request

from ..auth.decorators import require_auth
from ..database.repository import increment_user_balance
from ..database.services import get_user_orders
from ..errors import CheekyApiError
from ..utils import parse_as_decimal

bp = Blueprint("account", __name__, url_prefix="/account")


@bp.get("/credits")
@require_auth(["customer"])
def view_balance():
    return jsonify({"email": g.email, "balance": str(g.balance)}), 200


@bp.post("/credits")
@require_auth(["platform_api_key"])
def add_credits():
    amount_raw = request.form.get("amount")
    user = request.form.get("user")
    if not amount_raw or not user:
        raise CheekyApiError("Invalid request")

    amount = parse_as_decimal(amount_raw)
    if amount is None or amount <= 0:
        raise CheekyApiError("Amount must be a positive number")

    balance = increment_user_balance(user, amount)
    if balance is None:
        raise CheekyApiError("User not found")

    return jsonify({"email": user, "balance": str(balance)}), 200


@bp.route("/info", methods=["GET"])
@require_auth(["customer"])
def view_account_info():
    """Views the account information for a given user."""
    return jsonify(
        {
            "email": g.email,
            "name": g.name,
            "balance": str(g.balance),
            "orders": len(get_user_orders(g.email)),
        }
    ), 200
