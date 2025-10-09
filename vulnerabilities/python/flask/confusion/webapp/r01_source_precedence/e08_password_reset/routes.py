from flask import Blueprint, request

from .auth import authenticate_user
from .db import get_messages, reset_password

bp = Blueprint("source_precedence_password_reset", __name__, url_prefix="/example8")


# Note: This endpoint was FIXED by using request.values consistently for both authentication
# and message retrieval. This is the correct pattern - no parameter source confusion.
# However, see the password_reset endpoint below where the same developers made a mistake...
@bp.route("/messages", methods=["GET", "POST"])
def messages():
    """
    Retrieves messages for an authenticated user.

    Uses unified parameter resolution for both authentication and message retrieval,
    ensuring consistent parameter sourcing throughout the request lifecycle.
    """
    if not authenticate_user():
        return "Invalid user or password", 401

    # Retrieve messages using consistent request.values
    messages = get_messages(request.values.get("user", None))
    if messages is None:
        return "No messages found", 404

    return messages


# @unsafe[function]
# id: 8
# title: Password Reset Parameter Confusion
# notes: |
#   Developers "fixed" the messages endpoint but introduced a NEW vulnerability when adding
#   password reset functionality. Authentication uses request.values to verify WHO is making
#   the request, but the target user whose password gets reset comes from request.form only.
#
#   An attacker can authenticate with their own credentials in the query string while
#   specifying a victim's username in the form body, resetting the victim's password to
#   one they control. This enables full account takeover.
#
#   LESSON: This demonstrates how "apparent fixes" create false security. Same root cause
#   as Examples 2-7, but now enabling account takeover instead of just data disclosure.
#   The partial fix made developers careless when adding new features.
# @/unsafe
@bp.route("/password_reset", methods=["POST"])
def password_reset():
    """Resets a user's password after authentication."""
    # Use authenticate_user() instead of embedding check
    if not authenticate_user():
        return "Invalid user or password", 401

    # Target user and new password from form data (VULNERABILITY)
    target_user = request.form.get("user", None)
    new_password = request.form.get("new_password", None)

    if target_user is None or new_password is None:
        return "Missing required parameters", 400

    if reset_password(target_user, new_password):
        return {"status": "success", "user": target_user, "message": "Password updated"}
    else:
        return "User not found", 404
