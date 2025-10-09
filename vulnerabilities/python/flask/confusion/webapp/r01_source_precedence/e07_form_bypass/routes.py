from flask import Blueprint, request

from .auth import authenticate_user
from .db import get_messages

bp = Blueprint("source_precedence_form_bypass", __name__, url_prefix="/example7")


@bp.route("/messages", methods=["GET", "POST"])
def messages():
    """
    Retrieves messages for an authenticated user.

    Uses form-based authentication with unified parameter resolution for message retrieval.
    """
    if not authenticate_user():
        return "Invalid user or password", 401

    # Use request.values for flexible parameter resolution across query and form data
    messages = get_messages(request.values.get("user", None))
    if messages is None:
        return "No messages found", 404

    return messages
