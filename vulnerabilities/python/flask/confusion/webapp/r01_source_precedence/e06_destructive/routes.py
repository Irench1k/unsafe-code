from flask import Blueprint, request

from .auth import authenticate_user
from .db import delete_message, get_messages

bp = Blueprint("source_precedence_destructive", __name__, url_prefix="/example6")


# @unsafe[function]
# id: 6
# title: Destructive Parameter Source Confusion
# notes: |
#   Demonstrates parameter source confusion with a DELETE operation. Same root cause as
#   Examples 2-5, but now enabling destructive operations instead of just data disclosure.
#   Authentication uses query parameters while deletion target uses form body.
# @/unsafe
@bp.route("/messages", methods=["DELETE", "GET"])
def messages():
    """Manages user messages with list and delete operations."""
    if not authenticate_user():
        return "Invalid user or password", 401

    action = request.args.get("action", "delete")

    if action == "list":
        user = request.args.get("user")
        messages = get_messages(user)
        if messages is None:
            return "No messages found", 404
        return messages

    # Delete message - target user from form body (VULNERABILITY)
    target_user = request.form.get("user")
    message_index = int(request.args.get("index", 0))

    if delete_message(target_user, message_index):
        return {"status": "deleted", "user": target_user, "index": message_index}
    else:
        return "Message not found", 404
