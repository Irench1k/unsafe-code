from flask import Blueprint, request

from .auth import authenticate_principal
from .db import get_messages

bp = Blueprint("source_precedence_mixed_source", __name__, url_prefix="/example5")


@bp.route("/messages", methods=["GET", "POST"])
def messages():
    """
    Retrieves messages for an authenticated user.

    Combines flexible authentication with query-based message retrieval.
    """
    if not authenticate_principal(request):
        return "Invalid user or password", 401

    messages = get_messages(request.args.get("user", None))
    if messages is None:
        return "No messages found", 404
    return messages
