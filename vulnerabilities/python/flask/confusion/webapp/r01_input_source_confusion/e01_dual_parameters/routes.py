from decimal import Decimal

from flask import Blueprint, jsonify, request

from ..database import (
    Order,
    OrderItem,
    charge_user,
    create_order,
    db,
    get_menu_item,
    get_next_order_id,
    get_user,
)

bp = Blueprint("e01_dual_parameters", __name__)


@bp.route("/")
def index():
    return "Dual Parameters - Example 01\n"


@bp.route("/account/credits", methods=["GET"])
def view_balance():
    """Views the balance for a given user."""
    user_id = request.args.get("user_id")
    if not user_id:
        return jsonify({"error": "Missing 'user_id' query parameter."}), 400

    user = get_user(user_id)
    if not user:
        return jsonify({"error": f"User '{user_id}' not found."}), 404

    return jsonify({"user_id": user.user_id, "balance": str(user.balance)})


@bp.route("/menu", methods=["GET"])
def list_menu_items():
    """Lists all available menu items."""
    menu_list = [item.model_dump() for item in db["menu_items"].values()]
    return jsonify(menu_list)


@bp.route("/orders", methods=["GET"])
def list_orders():
    """Lists all created orders."""
    order_list = [order.model_dump(mode="json") for order in db["orders"].values()]
    return jsonify(order_list)


@bp.route("/orders", methods=["POST"])
def create_new_order():
    """Creates a new order."""
    user_id = request.form.get("user_id")
    if not user_id:
        return jsonify({"error": "Missing 'user_id' parameter."}), 400

    try:
        total_price = order_total_price(request.form)
        items = get_order_items(request.form)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    charge_user(user_id, total_price)

    new_order = Order(
        order_id=get_next_order_id(),
        total=total_price,
        user_id=user_id,
        items=items,
    )

    create_order(new_order)

    return jsonify(new_order.model_dump(mode="json")), 201


def order_total_price(form_data):
    """Calculates the total price of an order."""
    if "item" in form_data:
        item_id = form_data.get("item")
        if not item_id:
            raise ValueError("Pricing parameter 'item' cannot be empty.")
        menu_item = get_menu_item(item_id)
        if not menu_item:
            raise ValueError(f"Menu item '{item_id}' for pricing not found.")
        return menu_item.price

    item_ids = form_data.getlist("items")
    if not item_ids:
        raise ValueError("Request must contain 'item' or 'items' for pricing.")

    total_price = Decimal("0.0")
    for item_id in item_ids:
        if not item_id:
            continue
        menu_item = get_menu_item(item_id)
        if not menu_item:
            raise ValueError(f"Menu item '{item_id}' for pricing not found.")
        total_price += menu_item.price
    return total_price


def get_order_items(form_data):
    """Builds the list of items for an order."""
    item_ids = form_data.getlist("items")
    if not item_ids:
        item_id = form_data.get("item")
        if not item_id:
            raise ValueError("Request must contain 'item' or 'items' for fulfillment.")
        item_ids = [item_id]

    order_items = []
    for item_id in item_ids:
        if not item_id:
            continue
        menu_item = get_menu_item(item_id)
        if not menu_item:
            raise ValueError(f"Menu item '{item_id}' for order not found.")
        order_items.append(OrderItem(item_id=item_id, name=menu_item.name, price=menu_item.price))
    return order_items
