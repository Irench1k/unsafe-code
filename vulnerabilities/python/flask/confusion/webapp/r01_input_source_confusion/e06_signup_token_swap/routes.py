from decimal import Decimal

from flask import Blueprint, g, jsonify, request

from .auth import (
    customer_authentication_required,
    get_authenticated_user,
    protect_refunds,
    validate_api_key,
)
from .database import (
    add_item_to_cart,
    create_cart,
    get_all_menu_items,
    get_all_orders,
    get_cart,
    get_user,
    get_user_orders,
    reset_db,
    refund_user,
    save_order_securely,
    save_refund,
    set_balance,
)
from .models import Order, Refund
from .utils import (
    check_cart_price_and_delivery_fee,
    convert_item_ids_to_order_items,
    get_email_from_token,
    get_request_parameter,
    parse_as_decimal,
    register_new_user,
    send_verification_email,
    verify_user_verification_token,
)

bp = Blueprint("e06_signup_token_swap", __name__)


@bp.before_request
def middleware():
    """Security middleware to prevent future attacks."""
    # We don't accept order_id from the user to prevent order overwrite attacks.
    order_id = get_request_parameter("order_id")
    if order_id is not None:
        return jsonify({"error": "hacking attempt detected"}), 400


@bp.route("/")
def index():
    return "R01: Input Source Confusion - Signup Token Swap\n"


@bp.route("/account/credits", methods=["GET"])
@customer_authentication_required
def view_balance():
    """Views the balance for a given user."""
    return jsonify({"user_id": g.user.user_id, "balance": str(g.user.balance)}), 200


@bp.route("/account/info", methods=["GET"])
@customer_authentication_required
def view_account_info():
    """Views the account information for a given user."""
    return jsonify(
        {
            "email": g.user.user_id,
            "name": g.user.name,
            "balance": str(g.user.balance),
            "orders": len(get_user_orders(g.user.user_id)),
        }
    ), 200


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

    # Some users were "accidentally" giving negative tips, no more!
    tip = abs(Decimal(user_data.get("tip", 0)))

    # Price and delivery fee calculation is the same for both branches
    total_price, delivery_fee = check_cart_price_and_delivery_fee(cart.items)
    if not total_price:
        return jsonify({"error": "Item not available, sorry!"}), 400

    if g.user.balance < total_price + delivery_fee + tip:
        return jsonify({"error": "Insufficient balance"}), 400

    items = convert_item_ids_to_order_items(cart.items)

    safe_order_data = {
        "total": total_price + delivery_fee + tip,
        "user_id": g.user.user_id,
        "items": [item.model_dump() for item in items],
        "delivery_fee": delivery_fee,
        "tip": tip,
    }

    new_order = Order.model_validate({**user_data, **safe_order_data})

    save_order_securely(new_order)

    return jsonify(new_order.model_dump(mode="json")), 201


@bp.route("/orders/<order_id>/refund", methods=["POST"])
@customer_authentication_required
@protect_refunds
def refund_order(order_id):
    """Refunds an order."""
    reason = get_request_parameter("reason") or ""
    refund_amount_entered = parse_as_decimal(get_request_parameter("amount"))
    refund_amount = refund_amount_entered or Decimal("0.2") * g.order.total

    status = "auto_approved" if g.refund_is_auto_approved else "pending"

    refund = Refund(
        order_id=order_id,
        amount=refund_amount,
        reason=reason,
        status=status,
        auto_approved=g.refund_is_auto_approved,
    )

    if g.refund_is_auto_approved:
        refund_user(g.user.user_id, refund_amount)

    save_refund(refund)
    return jsonify(refund.model_dump(mode="json")), 200


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


@bp.route("/auth/register", methods=["POST"])
def register_user():
    """
    Registers a new user with an email verification.

    The handler gets called twice:

      1. Without a token:
        - Input: `email`
        - Output: `email` and `status` (failure if email is already taken)
        - Sends verification email to the user, with a token & URL

      2. With a token:
        - Input: `token`, `password`, `name`
        - Output: `email` and `status` (failure if the token invalid)
    """
    user_data = request.json
    if not user_data or not isinstance(user_data, dict):
        # Registration is only for new app & upcoming website, I don't think I need to support form anymore
        return jsonify({"status": "error", "message": "Invalid request!"}), 400

    password = user_data.get("password")
    name = user_data.get("name")
    token = user_data.get("token")
    email = user_data.get("email") or get_email_from_token(token)

    if not token:
        # First step: check email uniqueness and send verification email
        if not email or not isinstance(email, str):
            # Maybe add email validation here? The user should only get token if email is valid, so that's probably enough...
            return jsonify({"status": "error", "message": "email is required"}), 400

        if get_user(email):
            return jsonify({"status": "error", "message": "email already taken"}), 400

        return send_verification_email(email)

    # Second step: verify token and create user if token is valid
    if not email or not password or not name or not token:
        return jsonify(
            {"status": "error", "message": "email, password, name, and token are required"}
        ), 400

    if not verify_user_verification_token(token):
        return jsonify({"status": "error", "message": "Invalid token"}), 400

    return register_new_user(email, password, name)
