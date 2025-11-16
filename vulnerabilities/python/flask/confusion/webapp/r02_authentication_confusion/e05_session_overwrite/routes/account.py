from flask import Blueprint, g, jsonify, request

from ..auth.decorators import require_auth
from ..database.repository import increment_user_balance
from ..database.services import get_user_orders
from ..errors import CheekyApiError
from ..utils import parse_as_decimal

bp = Blueprint("account", __name__, url_prefix="/account")


@bp.get("/credits")
@require_auth(["cookies", "basic_auth"])
def view_balance():
    return jsonify({"email": g.email, "balance": str(g.balance)}), 200


@bp.post("/credits")
@require_auth(["restaurant_api_key"])
def add_credits():
    amount = request.form["amount"]
    user = request.form["user"]
    if not amount or not user:
        raise CheekyApiError("Invalid request")

    balance = increment_user_balance(user, parse_as_decimal(amount))
    return jsonify({"email": user, "balance": str(balance)}), 200


@bp.route("/info", methods=["GET"])
@require_auth(["cookies", "basic_auth"])
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
