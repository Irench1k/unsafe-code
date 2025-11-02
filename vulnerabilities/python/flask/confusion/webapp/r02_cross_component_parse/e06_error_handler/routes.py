"""Error handler example with fail-open vulnerability."""

from flask import Blueprint

from .auth import cross_account_access_control, require_auth
from .db import get_profile
from .security import sanitize_profile

bp = Blueprint("cross_component_error_handler", __name__, url_prefix="/example6")


# Mapping of known exceptions to safe messages
ERROR_MESSAGES = {
    ValueError: "Invalid input provided",
    KeyError: "Resource not found",
    PermissionError: "Access denied",
}


@bp.errorhandler(Exception)
def handle_error(error):
    """Error handler to sanitize uncaught exceptions."""
    error_type = type(error)

    # Replace the exception with a safe message
    if error_type in ERROR_MESSAGES:
        return {"error": ERROR_MESSAGES[error_type]}, 500

    return {"error": str(error)}, 500


@bp.after_request
def ensure_json(response):
    """Ensures all responses are JSON."""
    from flask import Response, jsonify

    if not isinstance(response, Response):
        return jsonify(response), response.status_code
    return response


# @unsafe[block]
# id: 5
# title: Error Handler with Fail-Open Vulnerability
# notes: |
#   Error handler sanitizes known exceptions but fails open for unexpected ones,
#   revealing full exception details. The view_profile function includes the full
#   profile (with password) in RuntimeError exceptions when validating username format.
#
#   When an attacker provides a username with suspicious characters, it triggers an
#   unknown exception type that leaks the password in the error response through the
#   fail-open error handler.
# @/unsafe


@bp.get("/profile/<username>/view")
@require_auth
def view_profile(username):
    """
    View profile data. We only check authentication by design, the users ARE allowed to view other users' profiles.
    """
    cross_account_access_control(username)

    profile = get_profile()
    if not profile:
        return {"error": "User not found"}, 404

    return sanitize_profile(profile), 200


# @/unsafe[block]
