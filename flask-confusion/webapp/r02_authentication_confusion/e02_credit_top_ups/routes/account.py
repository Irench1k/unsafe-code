from flask import Blueprint, g, jsonify, request

from ..auth.decorators import customer_authentication_required
from ..auth.helpers import authenticate_customer
from ..database.repository import get_platform_api_key
from ..database.services import get_user_orders, increment_user_balance
from ..errors import CheekyApiError
from ..utils import parse_as_decimal

bp = Blueprint("account", __name__, url_prefix="/account")


def _authenticate_platform():
    """Authenticates the platform."""
    return get_platform_api_key() == request.headers.get("X-Admin-API-Key")


@bp.route("/credits", methods=["GET", "POST"])
def view_balance():
    """
    Views or update the balance.

    GET: Authenticate customer and show their balance
    POST: Authenticate platform and add credits to the provided customer
    """
    # 1. Authenticate customer for GET, platform for POST
    if request.method == "GET" and not authenticate_customer():
        raise CheekyApiError("Unauthorized")

    if request.method == "POST" and not _authenticate_platform():
        raise CheekyApiError("Unauthorized")

    # 2. Return data or add credits, as required
    if request.form is not None and "amount" in request.form and "user" in request.form:
        amount = request.form["amount"]
        user = request.form["user"]

        if not amount or not user:
            raise CheekyApiError("Invalid request")

        balance = increment_user_balance(user, parse_as_decimal(amount))

    else:
        user = getattr(g, "email", None)
        balance = getattr(g, "balance", None)

    if user is None or balance is None:
        raise CheekyApiError("User not found")

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
