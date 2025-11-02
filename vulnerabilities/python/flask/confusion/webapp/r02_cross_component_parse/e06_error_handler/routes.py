"""Baseline example with verbose inline authentication."""

from flask import Blueprint, g, request

from .auth import cross_account_access_control, require_auth
from .db import create_message, get_messages, get_profile, update_profile
from .security import sanitize_profile

bp = Blueprint("error_handler", __name__, url_prefix="/example6")


# Mapping of known exceptions to safe messages
ERROR_MESSAGES = {
    ValueError: "Invalid input provided",
    KeyError: "Resource not found",
    PermissionError: "Access denied",
}


# @unsafe[block]
# id: 6
# part: 2
# @/unsafe
@bp.errorhandler(Exception)
def handle_error(error):
    """Error handler to sanitize uncaught exceptions."""
    error_type = type(error)
    print(f"error_type is {error_type} and error is {error}")

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


# @/unsafe[block]


@bp.get("/messages/list")
@require_auth
def list_messages():
    """Lists all messages for the authenticated user."""
    messages = get_messages(g.user)
    return {"user": g.user, "messages": messages}, 200


@bp.post("/messages/new")
@require_auth
def create_new_message():
    """Creates a new message from the authenticated user."""
    recipient = request.form.get("recipient")
    text = request.form.get("text", "")

    if not recipient:
        return {"error": "Recipient required"}, 400

    msg_id = create_message(g.user, recipient, text)
    return (
        {"message_id": msg_id, "sender": g.user, "recipient": recipient},
        201,
    )


# @unsafe[block]
# id: 6
# title: Error Handler with Fail-Open Vulnerability
# notes: |
#   In this example we showcase two important Flask features: error handler and
#   `after_request` middleware. They allow us to remove large amount of code
#   duplication. Compare routes.py in this example with the previous example e05.
#
#   The weakness lies withing the `handle_error` function which is meant to sanitize
#   error messages to prevent leaking sensitive data. However, when the `error_type`
#   does not correspond to any of the keys in the `ERROR_MESSAGES` dictionary,
#   the handler fails open and leaks the full exception.
#
#   What goes wrong:
#   1. The `profile_is_active` function receives `username` and `profile` parameters, but what exactly does it get?
#   2. The `username` argument is the verbatim user input from the path, but the `profile` is
#      the result of `get_profile()` which uses the same `username` input from the path - but
#      this time it is sanitized using `sanitize_username()`.
#   3. As a result, an attacker can craft a malicious `<username>` which would match existing user
#      when processed by `sanitize_username()`, but would cause a catastrophic error message
#      being logged due to an unhandled exception in `profile_is_active()` function.
#
#   This vulnerability has several layers of weaknesses which when overlap break user's confidentiality.
# @/unsafe
@bp.get("/profile/<username>/view")
@require_auth
def view_profile(username):
    """Views a user profile. We allow any authenticated user to view any other user's profile."""
    cross_account_access_control(username)

    profile = get_profile()
    if not profile:
        return {"error": "User not found"}, 404

    return sanitize_profile(profile), 200


# @/unsafe[block]


@bp.patch("/profile/<username>/edit")
@require_auth
def edit_profile(username):
    """Edits the authenticated user's profile."""
    display_name = request.form.get("display_name")
    bio = request.form.get("bio")

    if not display_name and not bio:
        return {"error": "No updates provided"}, 400

    success = update_profile(display_name, bio)
    if not success:
        return {"error": "Update failed"}, 500

    return {"status": "updated", "user": g.user}, 200
