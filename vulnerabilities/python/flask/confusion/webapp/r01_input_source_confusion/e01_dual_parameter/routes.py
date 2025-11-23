from decimal import Decimal

from flask import Blueprint, jsonify, request

from .auth import get_authenticated_user, validate_api_key
from .database import (
    create_order_and_charge_customer,
    get_all_menu_items,
    get_all_orders,
    get_user_orders,
    reset_db,
    set_balance,
)
from .e2e_helpers import require_e2e_auth
from .utils import check_price_and_availability, get_order_items

bp = Blueprint("e01_dual_params", __name__)


@bp.route("/")
def index():
    return "R01: Input Source Confusion - Dual Parameters\n"


@bp.route("/account/credits", methods=["GET"])
def view_balance():
    """Views the balance for a given user."""
    user = get_authenticated_user()
    if not user:
        return jsonify({"error": "Authentication required"}), 401

    return jsonify({"user_id": user.user_id, "balance": str(user.balance)}), 200


@bp.route("/menu", methods=["GET"])
def list_menu_items():
    """Lists all available menu items."""
    menu_list = [item.model_dump() for item in get_all_menu_items()]
    return jsonify(menu_list)


@bp.route("/orders", methods=["GET"])
def list_orders():
    """Customers can list their own orders, restaurant managers can list ALL of them."""

    # Customer -> List their own orders
    user = get_authenticated_user()
    if user:
        orders = get_user_orders(user.user_id)
        return jsonify([order.model_dump(mode="json") for order in orders])

    # Restaurant manager -> List all orders
    if validate_api_key():
        orders = get_all_orders()
        return jsonify([order.model_dump(mode="json") for order in orders])

    return jsonify({"error": "Unauthorized"}), 401


@bp.route("/orders", methods=["POST"])
def create_new_order():
    """Creates a new order."""
    user = get_authenticated_user()
    if not user:
        return jsonify({"error": "Authentication required"}), 401

    total_price = check_price_and_availability(request.form)
    if not total_price:
        return jsonify({"error": "Item not available, sorry!"}), 400

    if user.balance < total_price:
        return jsonify({"error": "Insufficient balance"}), 400

    items = get_order_items(request.form)

    new_order = create_order_and_charge_customer(total_price, user.user_id, items)
    return jsonify(new_order.model_dump(mode="json")), 201


@bp.route("/e2e/reset", methods=["POST"])
@require_e2e_auth
def e2e_reset():
    """E2E test helper: reset in-memory database to initial state."""
    reset_db()
    return jsonify({"status": "reset"}), 200


@bp.route("/e2e/balance", methods=["POST"])
@require_e2e_auth
def e2e_balance():
    """E2E test helper: set user balance to a specific amount."""
    payload = request.get_json(silent=True) or {}
    user_id = payload.get("user_id") or "sandy"
    amount = payload.get("balance")
    if amount is None:
        return jsonify({"error": "balance required"}), 400
    if not set_balance(user_id, Decimal(str(amount))):
        return jsonify({"error": "user not found"}), 404
    return jsonify({"status": "ok", "user_id": user_id, "balance": str(amount)}), 200
