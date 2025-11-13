from decimal import Decimal

from flask import Blueprint, g, jsonify, request

from .auth import (
    customer_authentication_required,
    get_authenticated_user,
    validate_api_key,
)
from .database import (
    _save_order_securely,
    add_item_to_cart,
    create_cart,
    get_all_menu_items,
    get_all_orders,
    get_cart,
    get_user_orders,
)
from .models import Order
from .utils import (
    check_cart_price_and_delivery_fee,
    convert_item_ids_to_order_items,
)

bp = Blueprint("e04_negative_tip", __name__)


def parse_as_decimal(value: str) -> Decimal:
    try:
        return Decimal(value)
    except ValueError:
        return None


def get_request_parameter(parameter):
    parameter_in_args = request.args.get(parameter)
    parameter_in_json = (
        request.is_json and isinstance(request.json, dict) and request.json.get(parameter)
    )
    parameter_in_form = request.form.get(parameter)

    return parameter_in_args or parameter_in_json or parameter_in_form


@bp.before_request
def middleware():
    """Security middleware to prevent future attacks."""
    # We don't accept order_id from the user to prevent order overwrite attacks.
    order_id = get_request_parameter("order_id")
    if order_id is not None:
        return jsonify({"error": "hacking attempt detected"}), 400

    # Now we check that the tip is valid (not negative).
    tip = get_request_parameter("tip")
    if tip is not None and parse_as_decimal(tip) < 0:
        return jsonify({"error": "tip cannot be negative"}), 400


@bp.route("/")
def index():
    return "R01: Input Source Confusion - Negative Tip\n"


@bp.route("/account/credits", methods=["GET"])
@customer_authentication_required
def view_balance():
    """Views the balance for a given user."""
    return jsonify({"user_id": g.user.user_id, "balance": str(g.user.balance)}), 200


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


@bp.route("/cart", methods=["POST"])
@customer_authentication_required
def create_new_cart():
    """
    Creates a new empty cart.

    This is step 1 of the new checkout flow. The cart gets an ID that
    the client will use in subsequent requests to add items.
    """
    new_cart = create_cart()
    return jsonify(new_cart.model_dump()), 201


@bp.route("/cart/<cart_id>/items", methods=["POST"])
@customer_authentication_required
def add_item_to_cart_endpoint(cart_id):
    """
    Adds a single item to an existing cart.

    This is step 2 of the new checkout flow. Can be called multiple times
    to add different items. Expects JSON body with item_id.

    Note: Flask's request.json automatically parses JSON bodies when
    Content-Type is application/json.
    """
    if not request.json:
        return jsonify({"error": "JSON body required"}), 400

    item_id = request.json.get("item_id")
    if not item_id:
        return jsonify({"error": "item_id is required"}), 400

    cart = get_cart(cart_id)
    if not cart:
        return jsonify({"error": "Cart not found"}), 404

    updated_cart = add_item_to_cart(cart_id, item_id)
    return jsonify(updated_cart.model_dump()), 200


@bp.route("/cart/<cart_id>/checkout", methods=["POST"])
@customer_authentication_required
def checkout_cart(cart_id):
    """Checks out a cart and creates an order."""
    cart = get_cart(cart_id)
    if not cart or not cart.items:
        return jsonify({"error": "Cart not found"}), 404

    # Get user input - handle both JSON and form data
    user_data = request.json if request.is_json else request.form
    tip = Decimal(user_data.get("tip", 0))

    # Price and delivery fee calculation is the same for both branches
    total_price, delivery_fee = check_cart_price_and_delivery_fee(cart.items)
    if not total_price:
        return jsonify({"error": "Item not available, sorry!"}), 400

    if g.user.balance < total_price + delivery_fee + tip:
        return jsonify({"error": "Insufficient balance"}), 400

    items = convert_item_ids_to_order_items(cart.items)

    safe_order_data = {
        "total": total_price + delivery_fee,
        "user_id": g.user.user_id,
        "items": [item.model_dump() for item in items],
        "delivery_fee": delivery_fee,
        "tip": tip,
    }

    new_order = Order.model_validate({**user_data, **safe_order_data})

    _save_order_securely(new_order)

    return jsonify(new_order.model_dump(mode="json")), 201
