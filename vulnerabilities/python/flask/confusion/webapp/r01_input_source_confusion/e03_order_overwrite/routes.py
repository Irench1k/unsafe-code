from decimal import Decimal

from flask import Blueprint, jsonify, request

from .auth import get_authenticated_user, validate_api_key
from .database import (
    _save_order_securely,
    add_item_to_cart,
    create_cart,
    create_order_and_charge_customer,
    get_all_menu_items,
    get_all_orders,
    get_cart,
    get_user_orders,
    reset_db,
    set_balance,
)
from .models import Order
from .utils import (
    calculate_delivery_fee,
    check_cart_price_and_delivery_fee,
    check_price_and_availability,
    convert_item_ids_to_order_items,
    get_order_items,
)

bp = Blueprint("e03_order_overwrite", __name__)


@bp.route("/")
def index():
    return "R01: Input Source Confusion - Order Overwrite\n"


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


# ============================================================
# OLD FLOW: Direct order creation (v101-v102)
# This endpoint is kept for backward compatibility but Sandy
# is migrating users to the new cart-based flow below.
# ============================================================


@bp.route("/orders", methods=["POST"])
def create_new_order():
    """
    Creates a new order directly from form data (the original flow).

    This endpoint is FIXED from e02:
    - Now only reads items from request.form (not request.values)
    - Delivery fee calculation is also fixed to use request.form only

    Students should verify this fix works before studying the new cart flow.
    """
    user = get_authenticated_user()
    if not user:
        return jsonify({"error": "Authentication required"}), 401

    delivery_address = request.form.get("delivery_address")
    if not delivery_address:
        return jsonify({"error": "delivery_address is required"}), 400

    total_price = check_price_and_availability(request.form)
    if not total_price:
        return jsonify({"error": "Item not available, sorry!"}), 400

    delivery_fee = calculate_delivery_fee(request.form)

    if user.balance < total_price + delivery_fee:
        return jsonify({"error": "Insufficient balance"}), 400

    items = get_order_items(request.form)

    new_order = create_order_and_charge_customer(
        total_price, user.user_id, items, delivery_fee, delivery_address
    )
    return jsonify(new_order.model_dump(mode="json")), 201


# ============================================================
# NEW FLOW: Cart-based checkout (v103+)
# Sandy is adding a shopping cart feature to improve UX.
# Users can now:
#   1. Create a cart
#   2. Add items to it (multiple requests)
#   3. Checkout when ready
# ============================================================


@bp.route("/cart", methods=["POST"])
def create_new_cart():
    """
    Creates a new empty cart.

    This is step 1 of the new checkout flow. The cart gets an ID that
    the client will use in subsequent requests to add items.
    """
    user = get_authenticated_user()
    if not user:
        return jsonify({"error": "Authentication required"}), 401

    new_cart = create_cart()
    return jsonify(new_cart.model_dump()), 201


@bp.route("/cart/<cart_id>/items", methods=["POST"])
def add_item_to_cart_endpoint(cart_id):
    """
    Adds a single item to an existing cart.

    This is step 2 of the new checkout flow. Can be called multiple times
    to add different items. Expects JSON body with item_id.

    Note: Flask's request.json automatically parses JSON bodies when
    Content-Type is application/json.
    """
    user = get_authenticated_user()
    if not user:
        return jsonify({"error": "Authentication required"}), 401

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
def checkout_cart(cart_id):
    """Checks out a cart and creates an order."""
    user = get_authenticated_user()
    if not user:
        return jsonify({"error": "Authentication required"}), 401

    cart = get_cart(cart_id)
    if not cart or not cart.items:
        return jsonify({"error": "Cart not found"}), 404

    # Get user input - handle both JSON and form data
    user_data = request.json if request.is_json else request.form

    # Price and delivery fee calculation is the same for both branches
    total_price, delivery_fee = check_cart_price_and_delivery_fee(cart.items)
    if not total_price:
        return jsonify({"error": "Item not available, sorry!"}), 400

    if user.balance < total_price + delivery_fee:
        return jsonify({"error": "Insufficient balance"}), 400

    items = convert_item_ids_to_order_items(cart.items)

    safe_order_data = {
        "total": total_price + delivery_fee,
        "user_id": user.user_id,
        "items": [item.model_dump() for item in items],
        "delivery_fee": delivery_fee,
    }

    new_order = Order.model_validate({**user_data, **safe_order_data})

    _save_order_securely(new_order)

    return jsonify(new_order.model_dump(mode="json")), 201


def _require_platform_admin():
    user = get_authenticated_user()
    if not user or user.user_id != "sandy":
        return None
    return user


@bp.route("/platform/reset", methods=["POST"])
def platform_reset():
    if not _require_platform_admin():
        return jsonify({"error": "Forbidden"}), 403
    reset_db()
    return jsonify({"status": "reset"}), 200


@bp.route("/platform/balance", methods=["POST"])
def platform_balance():
    if not _require_platform_admin():
        return jsonify({"error": "Forbidden"}), 403
    payload = request.get_json(silent=True) or {}
    user_id = payload.get("user_id") or "sandy"
    amount = payload.get("balance")
    if amount is None:
        return jsonify({"error": "balance required"}), 400
    if not set_balance(user_id, Decimal(str(amount))):
        return jsonify({"error": "user not found"}), 404
    return jsonify({"status": "ok", "user_id": user_id, "balance": str(amount)}), 200
