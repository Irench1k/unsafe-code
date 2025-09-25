from flask import Blueprint, Response, g, jsonify, request
from pydantic import ValidationError

from ..decorator import basic_auth, check_group_membership, check_if_admin
from ..schemas.groups import (CreateGroup, CreateGroupMember, GroupDTO, GroupMembersDTO,
                             UpdateGroupSettings)
from ..services.groups import GroupService
from ..services.users import UserService

groups_bp = Blueprint("groups", __name__)

@groups_bp.post("/")
@basic_auth
def create_group() -> Response | tuple[Response, int]:
    """
    Create a new group with cross-category uniqueness check. Any user can create a group.

    POST /groups

    Accepts a JSON body:
    {
        "name": "string",
        "description": "string",
        "users": [{"role": "member" | "admin", "user": "string"}]
    }
    """
    try:
        cmd = CreateGroup.model_validate_json(request.data)
    except ValidationError as e:
        return jsonify({"status": "error", "message": str(e)}), 400

    group_service = GroupService()
    user_service = UserService()

    # Check if group or user already exists (cross-category uniqueness)
    existing_group = group_service.groups.get_by_name(cmd.name)
    if existing_group:
        return jsonify({"status": "error", "message": "Group already exists"}), 400

    existing_user = user_service.users.get_by_email(cmd.name)
    if existing_user:
        return jsonify({"status": "error", "message": "Name conflicts with existing user"}), 400

    try:
        dto: GroupDTO = group_service.create_group(g.user, cmd)
        return jsonify(dto.model_dump())
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@groups_bp.get("/<group>/members")
@basic_auth
@check_group_membership
def get_group_members(group: str) -> Response | tuple[Response, int]:
    """
    Get all members of a group

    GET /groups/{group}/members
    """
    group_service = GroupService()
    dto: GroupMembersDTO = group_service.get_group_members(group)
    return jsonify(dto.model_dump())


@groups_bp.post("/<group>/members")
@basic_auth
@check_if_admin
def add_group_member(group: str) -> Response | tuple[Response, int]:
    """
    Add a member to a group

    POST /groups/{group}/members

    Accepts a JSON body:
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


@groups_bp.patch("/<group>")
@basic_auth
@check_if_admin
def update_group(group: str) -> Response | tuple[Response, int]:
    """
    Update group settings (replace all members)

    PATCH /groups/{group}

    Accepts a JSON body:
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