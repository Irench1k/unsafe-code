import logging
import traceback

from flask import request

from .. import bp
from ..errors import CheekyApiError
from ..utils import error_response, get_param

logger = logging.getLogger(__name__)


@bp.errorhandler(CheekyApiError)
def handle_cheeky_api_error(error: CheekyApiError):
    """Handle Cheeky API errors."""
    return error_response(error.message)


@bp.errorhandler(Exception)
def handle_exception(error: Exception):
    """Handle all other exceptions."""
    logger.error(f"Unhandled exception: {error}\n{traceback.format_exc()}")
    return error_response("Something went wrong", 500)


@bp.before_request
def protect_order_id():
    """Security middleware to prevent future attacks."""
    # We don't accept order_id from the user to prevent order overwrite attacks.
    order_id = get_param("order_id")
    if order_id is not None:
        raise CheekyApiError("hacking attempt detected")


def require_json_for_mutations():
    """
    Enforce JSON-only bodies for mutation requests.

    Part of our security hardening: all POST/PATCH/PUT/DELETE requests
    must use JSON bodies. This prevents parameter confusion attacks where
    attackers exploit differences between query params and body params.
    """
    if request.method not in ("POST", "PATCH", "PUT", "DELETE"):
        return

    if request.content_length and request.content_length > 0:
        if not request.is_json:
            raise CheekyApiError("Content-Type must be application/json")
        if not isinstance(request.json, dict):
            raise CheekyApiError("Request body must be a JSON object")
