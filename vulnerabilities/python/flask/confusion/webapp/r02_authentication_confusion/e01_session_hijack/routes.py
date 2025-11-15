from decimal import Decimal

from flask import g, jsonify, request, session

from . import bp
from .auth.authenticators import CredentialAuthenticator, CustomerAuthenticator
from .auth.decorators import (
    customer_authentication_required,
    protect_refunds,
    verify_order_access,
)
from .auth.helpers import authenticate_customer, validate_api_key
from .database.models import Order, Refund
from .database.repository import (
    find_all_menu_items,
    find_all_orders,
    find_cart_by_id,
    find_user_by_id,
    save_refund,
)
from .database.services import (
    add_item_to_cart,
    apply_signup_bonus,
    create_cart,
    create_user,
    get_user_orders,
    refund_user,
    save_order_securely,
)
from .errors import CheekyApiError
from .utils import (
    check_cart_price_and_delivery_fee,
    convert_item_ids_to_order_items,
    get_request_parameter,
    parse_as_decimal,
    send_verification_email,
)


@bp.route("/")
def index():
    return "R02: Authentication Confusion - Session Hijack\n"


@bp.route("/account/credits", methods=["GET"])
@customer_authentication_required
def view_balance():
    """Views the balance for a given user."""
    return jsonify({"email": g.email, "balance": str(g.balance)}), 200


@bp.route("/account/info", methods=["GET"])
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


@bp.route("/menu", methods=["GET"])
def list_menu_items():
    """Lists all available menu items."""
    menu_list = [item.model_dump() for item in find_all_menu_items()]
    return jsonify(menu_list)


@bp.get("/orders")
def list_orders():
    """Customers can list their own orders, restaurant managers can list ALL of them."""

    # Customer -> List their own orders
    if authenticate_customer():
        orders = get_user_orders(g.email)
        return jsonify([order.model_dump(mode="json") for order in orders])

    # Restaurant manager -> List all orders
    if validate_api_key():
        orders = find_all_orders()
        return jsonify([order.model_dump(mode="json") for order in orders])

    raise CheekyApiError("Unauthorized")


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
        raise CheekyApiError("JSON body required")

    item_id = request.json.get("item_id")
    if not item_id:
        raise CheekyApiError("item_id is required")

    cart = find_cart_by_id(cart_id)
    if not cart:
        raise CheekyApiError("Cart not found")

    updated_cart = add_item_to_cart(cart_id, item_id)
    return jsonify(updated_cart.model_dump()), 200


@bp.route("/cart/<cart_id>/checkout", methods=["POST"])
@customer_authentication_required
def checkout_cart(cart_id):
    """Checks out a cart and creates an order."""
    cart = find_cart_by_id(cart_id)
    if not cart or not cart.items:
        raise CheekyApiError("Cart not found")

    # Get user input - handle both JSON and form data
    user_data = request.json if request.is_json else request.form

    # Some users were "accidentally" giving negative tips, no more!
    tip = abs(Decimal(user_data.get("tip", 0)))

    # Price and delivery fee calculation is the same for both branches
    total_price, delivery_fee = check_cart_price_and_delivery_fee(cart.items)
    if not total_price:
        raise CheekyApiError("Item not available, sorry!")

    if g.balance < total_price + delivery_fee + tip:
        raise CheekyApiError("Insufficient balance")

    items = convert_item_ids_to_order_items(cart.items)

    safe_order_data = {
        "total": total_price + delivery_fee + tip,
        "user_id": g.email,
        "items": [item.model_dump() for item in items],
        "delivery_fee": delivery_fee,
        "tip": tip,
    }

    new_order = Order.model_validate({**user_data, **safe_order_data})
    save_order_securely(new_order)

    return jsonify(new_order.model_dump(mode="json")), 201


@bp.route("/orders/<order_id>/refund", methods=["POST"])
@customer_authentication_required
@verify_order_access
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
        refund_user(g.email, refund_amount)

    save_refund(refund)
    return jsonify(refund.model_dump(mode="json")), 200


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
    if not request.json.get("token"):
        # First step: the `email` parameter is UNAUTHENTICATED, do not trust it!
        unvalidated_email = request.json.get("email")
        if not unvalidated_email:
            raise CheekyApiError("email is required")

        if find_user_by_id(unvalidated_email):
            raise CheekyApiError("email already taken")

        return send_verification_email(unvalidated_email)
    elif g.email_confirmed:
        # Second step, token gets verified in middleware, setting trusted g.email based on it
        create_user(g.email, request.json.get("password"), request.json.get("name"))
        apply_signup_bonus(g.email)
        return jsonify({"status": "user_created", "email": g.email}), 200

    raise CheekyApiError("Registration failed, don't try again!")


@bp.route("/auth/login", methods=["POST"])
def login_user():
    """Login endpoint for website - accepts JSON credentials."""
    authenticator = CredentialAuthenticator.from_json()

    if not authenticator.authenticate():
        raise CheekyApiError("Invalid email or password")

    # Set session for future requests
    session["email"] = g.email

    return jsonify({"message": "Login successful"}), 200


@bp.route("/auth/logout", methods=["POST"])
def logout_user():
    """Logs out the user."""
    authenticator = CustomerAuthenticator()

    if not authenticator.authenticate():
        raise CheekyApiError("You are not logged in!")

    session.pop("email", None)
    return jsonify({"message": "Logout successful"}), 200
