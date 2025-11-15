import traceback

from flask import g, jsonify, request

from .. import bp
from ..database.repository import user_exists
from ..errors import CheekyApiError
from ..utils import get_email_from_token, get_request_parameter
from .helpers import verify_user_registration


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
def protect_order_id():
    """Security middleware to prevent future attacks."""
    # We don't accept order_id from the user to prevent order overwrite attacks.
    order_id = get_request_parameter("order_id")
    if order_id is not None:
        raise CheekyApiError("hacking attempt detected")
