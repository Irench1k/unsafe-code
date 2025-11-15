from flask import Blueprint, g, jsonify

from ..auth.decorators import customer_authentication_required
from ..database.services import get_user_orders

bp = Blueprint("account", __name__, url_prefix="/account")


@bp.get("/credits")
@customer_authentication_required
def view_balance():
    """Views the balance for a given user."""
    return jsonify({"email": g.email, "balance": str(g.balance)}), 200


@bp.get("/info")
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
