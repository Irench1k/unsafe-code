from flask import Blueprint, request

from .auth import authenticate_principal
from .messages import messages_delete, messages_get

bp = Blueprint("source_precedence_truthy_or", __name__, url_prefix="/example5")


@bp.get("/users/me/messages")
def list_messages():
    """
    Retrieves messages for an authenticated user.

    GET /messages?user=mr.krabs&password=money
    """
    if not authenticate_principal(request):
        return "Invalid user or password", 401

    return messages_get(request.args.get("user"))


# @unsafe[block]
# id: 5
# title: Truthy-OR Parameter Precedence
# part: 1
# notes: |
#   Demonstrates a subtle vulnerability in "flexible" parameter resolution. The auth
#   function resolves credentials via flexible fallback logic. Meanwhile, the message 
#   deletion function only checks the form parameters (the request body).
#
#   The main function here is `_resolve`, which merges parameter sources with a
#   specific priority: it first checks the URL query string (`request.args`) and only
#   falls back to the request body (`request.form`) if the parameter is not in the URL.
#   This allows an attacker to craft a request where the `user` parameter in the URL
#   is their own (to pass authentication), while the `user` parameter in the body
#   belongs to the victim (to target the action).
#
#   This DELETE endpoint demonstrates message destruction rather than unauthorized
#   reading—attackers can erase evidence or disrupt communications.
# @/unsafe
@bp.delete("/users/me/messages")
def delete_messages():
    """
    Manages user messages with delete operations.

    POST /messages
    user=mr.krabs&password=money&index=0&count=1
    """
    if not authenticate_principal(request):
        return "Invalid user or password", 401

    user = str(request.form.get("user"))
    index = int(request.form.get("index", 0))
    count = int(request.form.get("count", 1))

    deleted_messages_count = messages_delete(user, index, count)
    return {"status": "deleted", "user": user, "index": index, "count": deleted_messages_count}
# @/unsafe[block]
