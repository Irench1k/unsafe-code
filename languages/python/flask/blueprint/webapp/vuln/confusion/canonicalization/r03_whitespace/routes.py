from flask import Blueprint, request, jsonify

from pydantic import ValidationError

from .decorator import basic_auth, check_group_membership
from .database import get_group_messages, add_group
from .database.models import Group

bp = Blueprint("whitespace", __name__)


# @unsafe[block]
# id: 20
# title: Whitespace Canonicalization
# notes: |
#   TBD
# @/unsafe
@bp.get("/example20/groups/<group>/messages")
@basic_auth
@check_group_membership
def example20(group):
    messages = get_group_messages(group)
    # Each `Message` model can be converted to a dictionary using `model_dump()`
    # and to a JSON string using `model_dump_json()`, however messages is a list[Message]
    # so we need to iterate over it and convert each message to a dictionary manually
    return jsonify([m.model_dump() for m in messages])

@bp.post("/example20/groups")
@basic_auth
def example20_post():
    """Create a new group.

    Accepts a POST request with a JSON body:
    {
        "name": "string",
        "users": [{"role": "member" | "admin", "user": "string"}],
        "messages": [{"from_user": "string", "message": "string"}]
    }
    """
    try:
        group_request = Group.model_validate_json(request.data)
    except ValidationError as e:
        return {"status": "error", "message": str(e)}, 400

    add_group(group_request)
    return jsonify({"status": "ok"})
# @/unsafe[block]
