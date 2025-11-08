from flask import Blueprint, request

from .auth import authenticate_principal
from .messages import messages_delete, messages_get

bp = Blueprint("source_precedence_dict_get_default", __name__, url_prefix="/example6")


# @unsafe[block]
# id: 6
# title: dict.get() Default Parameter Precedence
# part: 1
# notes: |
#   The vulnerability shown in example 5 was fixed by reversing priority of parameters
#   in the merge function `_resolve`. However, this introduces a new vulnerability in
#   the message retrieval function.
#
#   Note that internet browsers and many web servers refuse body parameters for GET,
#   however Flask does support them, opening an attack vector for the attacker.
# @/unsafe
@bp.get("/users/me/messages")
def list_messages():
    """
    Retrieves messages for an authenticated user.

    GET /messages?user=mr.krabs&password=money
    """
    if not authenticate_principal(request):
        return "Invalid user or password", 401

    return messages_get(request.args.get("user"))
# @/unsafe[block]


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
