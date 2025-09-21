from flask import Blueprint, request, jsonify

from pydantic import ValidationError

from .decorator import basic_auth, check_group_membership, check_if_admin
from .database import get_group_messages, create_new_group, update_existing_group, add_member, group_exists
from .database.models import Group
from .database.models import GroupMember

bp = Blueprint("whitespace_2", __name__)


# @unsafe[block]
# id: 22
# title: Whitespace Canonicalization
# notes: |
#   TBD
# @/unsafe
@bp.get("/example22/groups/<group>/messages")
@basic_auth
@check_group_membership
def example22(group):
    messages = get_group_messages(group)
    
    return jsonify([m.model_dump() for m in messages])

@bp.post("/example22/groups/<group>")
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

@bp.post("/example22/groups")
@basic_auth
def create_group():
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

    if group_exists(request.json.get("name", None)):
        return {"status": "error", "message": "Group already exists!"}, 400
    
    create_new_group(group_request)
    return jsonify({"status": "ok"})

@bp.post("/example22/groups/<group>")
@basic_auth
@check_if_admin
def update_group(group):
    """Create a new group.

    Accepts a POST request with a JSON body:
    {
        "users": [{"role": "member" | "admin", "user": "string"}],
        "messages": [{"from_user": "string", "message": "string"}]
    }
    """
    try:
        group_request = Group.model_validate_json({
            "name": group,
            "users": request.json.get("users", None),
            "messages": request.json.get("messages", None)
        })
    except ValidationError as e:
        return {"status": "error", "message": str(e)}, 400

    update_existing_group(group_request)
    return jsonify({"status": "ok"})