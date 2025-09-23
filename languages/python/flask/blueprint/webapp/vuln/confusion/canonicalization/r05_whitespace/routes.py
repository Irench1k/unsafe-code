from flask import Blueprint, Response, request, jsonify, g

from pydantic import ValidationError

from .decorator import basic_auth, check_group_membership, check_if_admin
from .services.groups import GroupService
from .services.messages import MessageService
from .schemas.groups import CreateGroupMember, CreateGroup, UpdateGroupSettings, GroupDTO
from .schemas.messages import MessagesDTO

bp = Blueprint("sqlalchemy", __name__)


# @unsafe[block]
# id: 22
# title: Whitespace Canonicalization
# notes: |
#   TBD
# @/unsafe
@bp.get("/example22/groups/<group>/messages")
@basic_auth
@check_group_membership
def example22(group: str) -> Response:
    message_service = MessageService()
    dto: MessagesDTO = message_service.get_group_messages(group)
    return jsonify(dto.model_dump())
# @/unsafe[block]

@bp.post("/example22/groups/<group>")
@basic_auth
@check_if_admin
def add_group_member(group: str) -> Response:
    """
    Accepts a POST request with a JSON body:
    {
        "role": "member" | "admin",
        "user": "string"
    }
    """
    try:
        cmd = CreateGroupMember.model_validate_json(request.data)
    except ValidationError as e:
        return jsonify({"status": "error", "message": str(e)}), 400
    
    group_service = GroupService()
    dto: GroupDTO = group_service.add_member(group, cmd)
    return jsonify(dto.model_dump())

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
        cmd = CreateGroup.model_validate_json(request.data)
    except ValidationError as e:
        return jsonify({"status": "error", "message": str(e)}), 400
    
    group_service = GroupService()
    dto: GroupDTO = group_service.create_group(g.user, cmd)
    return jsonify(dto.model_dump())

@bp.post("/example22/groups/<group>")
@basic_auth
@check_if_admin
def update_group(group: str) -> Response:
    """Create a new group.

    Accepts a POST request with a JSON body:
    {
        "users": [{"role": "member" | "admin", "user": "string"}]
    }
    """
    try:
        cmd = UpdateGroupSettings.model_validate_json(request.data)
    except ValidationError as e:
        return jsonify({"status": "error", "message": str(e)}), 400
    
    group_service = GroupService()
    dto: GroupDTO = group_service.update_group(group, cmd)
    return jsonify(dto.model_dump())
