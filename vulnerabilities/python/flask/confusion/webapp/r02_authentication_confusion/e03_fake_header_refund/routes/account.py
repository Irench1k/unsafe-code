from flask import Blueprint, g, jsonify, request

from ..auth.decorators import customer_authentication_required
from ..auth.helpers import authenticate_customer
from ..database.repository import get_platform_api_key, increment_user_balance
from ..database.services import get_user_orders
from ..errors import CheekyApiError
from ..utils import parse_as_decimal

bp = Blueprint("account", __name__, url_prefix="/account")


def _authenticate_platform():
    """Authenticates the platform."""
    return get_platform_api_key() == request.headers.get("X-Admin-API-Key")


@bp.get("/credits")
@customer_authentication_required
def view_balance():
    return jsonify({"email": g.email, "balance": str(g.balance)}), 200


@bp.post("/credits")
def add_credits():
    if not _authenticate_platform():
        raise CheekyApiError("Unauthorized")

    amount = request.form["amount"]
    user = request.form["user"]
    if not amount or not user:
        raise CheekyApiError("Invalid request")

    balance = increment_user_balance(user, parse_as_decimal(amount))
    return jsonify({"email": user, "balance": str(balance)}), 200


@bp.route("/info", methods=["GET"])
@customer_authentication_required
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
