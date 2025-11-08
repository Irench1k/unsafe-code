from flask import Blueprint, request, jsonify

from pydantic import ValidationError

from .decorator import basic_auth, check_group_membership
from .database import get_group_messages, add_group
from .database.models import Group

bp = Blueprint("whitespace", __name__)


# @unsafe[block]
# id: 3
# title: Whitespace Canonicalization
# notes: |
#   This is a classic whitespace confusion attack - two parts of the code handle whitespace differently:
#   - strip() only removes leading/trailing whitespace
#   - replace(" ", "") removes ALL whitespace
#
#   So here's what happens:
#   - @check_group_membership uses strip() - sees "staff @krusty-krab.sea" and keeps the middle space
#   - example3 uses replace() - turns "staff @krusty-krab.sea" into "staff@krusty-krab.sea"
#
#   The attack: Plankton creates "staff @krusty-krab.sea" (with space), gets authorized for HIS group,
#   but the code actually fetches messages from "staff@krusty-krab.sea" (Mr. Krabs' group).
# @/unsafe
@bp.get("/example3/groups/<group>/messages")
@basic_auth
@check_group_membership
def example3(group):
    # Mobile users tend to send requests with whitespaces due to autocompletion.
    group_no_whitespace = group.replace(" ", "")
    messages = get_group_messages(group_no_whitespace)

    return jsonify([m.model_dump() for m in messages])

@bp.post("/example3/groups")
@basic_auth
def example3_post():
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
