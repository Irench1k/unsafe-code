from flask import Blueprint, request

from .auth import authenticate_user
from .db import messages_get

bp = Blueprint("source_precedence_cross_module", __name__, url_prefix="/example4")


# @unsafe[block]
# id: 4
# title: Cross-Module Parameter Source Confusion
# part: 1
# notes: |
#   Confusion becomes even harder to detect when business logic is split into separate
#   modules. Here the auth module uses form-based credentials which is secure on its
#   own but inconsistent with the `messages_get` receiving a query string parameter.
#
#   Note that each file looks reasonable in isolation.
# @/unsafe
@bp.post("/users/me/messages")
def list_messages():
    """
    Retrieves messages for an authenticated user.

    Delegates authentication to a shared utility function while handling
    message retrieval directly in the endpoint.
    """
    if not authenticate_user():
        return "Invalid user or password", 401

    return messages_get(request.args.get("user"))
# @/unsafe[block]
