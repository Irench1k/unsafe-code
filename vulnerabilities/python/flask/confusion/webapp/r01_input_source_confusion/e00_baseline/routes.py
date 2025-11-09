from flask import Blueprint, jsonify, request
from .auth import get_authenticated_user, validate_api_key
from .utils import check_price_and_availability, get_order_items
from .database import (
    create_order_and_charge_customer,
    get_all_orders,
    get_user_orders,
    get_all_menu_items,
)

bp = Blueprint("e00_baseline", __name__)


@bp.route("/")
def index():
    return "R01: Input Source Confusion - Baseline\n"


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

    total_price = check_price_and_availability(request.form.get("item"))
    if not total_price:
        return jsonify({"error": "Item not available, sorry!"}), 400

    if user.balance < total_price:
        return jsonify({"error": "Insufficient balance"}), 400

    items = get_order_items(request.form)

    new_order = create_order_and_charge_customer(total_price, user.user_id, items)
    return jsonify(new_order.model_dump(mode="json")), 201
