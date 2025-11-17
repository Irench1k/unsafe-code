import logging
import traceback

from flask import jsonify

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
