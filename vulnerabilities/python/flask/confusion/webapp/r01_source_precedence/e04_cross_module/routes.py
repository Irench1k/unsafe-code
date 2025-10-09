from flask import Blueprint, request

from .auth import authenticate_user
from .db import get_messages

bp = Blueprint("source_precedence_cross_module", __name__)


# @unsafe[block]
# id: 4
# part: 3
# @/unsafe
@bp.route("/example4", methods=["GET", "POST"])
def example4():
    """
    Retrieves messages for an authenticated user.

    Delegates authentication to a shared utility function while handling
    message retrieval directly in the endpoint.
    """
    if not authenticate_user():
        return "Invalid user or password", 401

    messages = get_messages(request.form.get("user", None))
    if messages is None:
        return "No messages found", 404

    return messages


# @/unsafe[block]
