import traceback

from flask import g, jsonify, request

from .. import bp
from ..database import get_order, get_user_orders, user_exists
from ..errors import CheekyApiError
from ..utils import get_email_from_token, get_request_parameter
from .helpers import get_authenticated_user, validate_api_key, verify_user_registration


@bp.errorhandler(CheekyApiError)
def handle_cheeky_api_error(error: CheekyApiError):
    """Handle Cheeky API errors."""
    return jsonify({"error": error.message}), 400


@bp.errorhandler(Exception)
def handle_exception(error: Exception):
    """Handle all other exceptions."""
    print(f"Exception: {error}")
    print(traceback.format_exc())
    return jsonify({"error": "Something went wrong"}), 500


@bp.before_request
def protect_registration_flow():
    """Authenticate user via email verification flow during the registration process."""
    token = request.is_json and request.json.get("token")
    print("protect_registration_flow", token)
    if token and verify_user_registration(token):
        g.email_confirmed = True
        g.email = get_email_from_token(token)
        # We check email uniqueness before sending the verification email,
        # but just in case let's check again here to prevent another hacking attempt
        g.email = g.email if not user_exists(g.email) else None
    else:
        # The token is expired, or maybe this isn't even a registration request
        g.email_confirmed = False


@bp.before_request
def protect_order_id():
    """Security middleware to prevent future attacks."""
    # We don't accept order_id from the user to prevent order overwrite attacks.
    order_id = get_request_parameter("order_id")
    if order_id is not None:
        raise CheekyApiError("hacking attempt detected")


@bp.before_request
def authenticate_user():
    # Moved from Basic Auth decorator
    g.user = get_authenticated_user()
    if g.user:
        g.is_customer = True
        g.email = g.user.user_id
        g.name = g.user.name
        g.balance = g.user.balance
        g.orders = get_user_orders(g.user.user_id)

    # Api-key
    g.is_restaurant_manager = validate_api_key()

    # Order
    g.order = get_order(request.view_args.get("order_id"))
