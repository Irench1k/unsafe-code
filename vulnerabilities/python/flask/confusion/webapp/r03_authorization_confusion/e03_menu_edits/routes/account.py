from flask import Blueprint, g

from ..auth.decorators import require_auth
from ..database.repository import increment_user_balance
from ..database.services import get_user_orders
from ..errors import CheekyApiError
from ..utils import get_decimal_param, get_param, success_response

bp = Blueprint("account", __name__, url_prefix="/account")


@bp.get("/credits")
@require_auth(["customer"])
def view_balance():
    return success_response({"email": g.email, "balance": str(g.balance)})


@bp.post("/credits")
@require_auth(["platform_api_key"])
def add_credits():
    """Add credits to a user's account. Platform-only."""
    amount = get_decimal_param("amount")
    user = get_param("user")
    if not amount or not user:
        raise CheekyApiError("Invalid request")

    balance = increment_user_balance(user, amount)
    return success_response({"email": user, "balance": str(balance)})


@bp.route("/info", methods=["GET"])
@require_auth(["customer"])
def view_account_info():
    """Views the account information for a given user."""
    return success_response(
        {
            "email": g.email,
            "name": g.name,
            "balance": str(g.balance),
            "orders": len(get_user_orders(g.user_id)),
        }
    )
