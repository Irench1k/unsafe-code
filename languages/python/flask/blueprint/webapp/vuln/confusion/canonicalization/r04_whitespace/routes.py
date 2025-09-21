from flask import Blueprint, request, jsonify

from pydantic import ValidationError

from .decorator import basic_auth, check_group_membership, check_if_admin
from .database import get_group_messages, add_group, add_member
from .database.models import Group
from .database.models import GroupMember

bp = Blueprint("whitespace_2", __name__)


# @unsafe[block]
# id: 21
# title: Whitespace Canonicalization
# notes: |
#   TBD
# @/unsafe
@bp.get("/example21/groups/<group>/messages")
@basic_auth
@check_group_membership
def example21(group):
    messages = get_group_messages(group)
    
    return jsonify([m.model_dump() for m in messages])

@bp.post("/example21/groups/<group>")
@basic_auth
@check_if_admin
def add_group_member(group):
    """
    Accepts a POST request with a JSON body:
    {
        "role": "member" | "admin",
        "user": "string"
    }
    """
    try:
        member_request = GroupMember.model_validate_json(request.data)
    except ValidationError as e:
        return {"status": "error", "message": str(e)}, 400
    
    try:
        add_member(group, member_request)
    except Exception as e:
        return {"status": "error", "message": str(e)}, 400
        
    return jsonify({"status": "ok"})
# @/unsafe[block]

@bp.post("/example21/groups")
@basic_auth
def example21_post():
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
