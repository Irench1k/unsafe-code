import bcrypt
from flask import Blueprint, Response, g, jsonify, request
from pydantic import ValidationError

from .decorator import basic_auth, check_group_membership, check_if_admin
from .schemas.groups import (CreateGroup, CreateGroupMember, GroupDTO, GroupMembersDTO,
                             UpdateGroupSettings)
from .schemas.messages import MessagesDTO
from .schemas.organizations import CreateOrganization
from .schemas.users import CreateUser, UserDTO
from .services.groups import GroupService
from .services.messages import MessageService
from .services.organizations import OrganizationService
from .services.users import UserService

bp = Blueprint("sqlalchemy", __name__)

# @unsafe[block]
# id: 22
# title: Whitespace Canonicalization
# notes: |
# @/unsafe
@bp.get("/example22/groups/<group>/messages")
@basic_auth
@check_group_membership
def example22(group: str) -> Response:
    # Mobile users tend to send requests with whitespaces due to autocompletion.
    message_service = MessageService()
    dto: MessagesDTO = message_service.get_group_messages(group)
    return jsonify(dto.model_dump())
# @/unsafe[block]

@bp.post("/example22/groups/<group>/members")
@basic_auth
@check_if_admin
def add_group_member(group: str) -> Response | tuple[Response, int]:
    """
    Accepts a POST request with a JSON body:
    {
        "role": "member" | "admin",
        "user": "string"
    }
    """
    # Mobile users tend to send requests with whitespaces due to autocompletion.
    
    try:
        cmd = CreateGroupMember.model_validate_json(request.data)
    except ValidationError as e:
        return jsonify({"status": "error", "message": str(e)}), 400

    group_service = GroupService()
    dto: GroupDTO = group_service.add_member(group, cmd)
    return jsonify(dto.model_dump())

@bp.get("/example22/groups/<group>/members")
@basic_auth
@check_group_membership
def get_group_members(group: str) -> Response | tuple[Response, int]:
    """Get all members of a group"""
    # Mobile users tend to send requests with whitespaces due to autocompletion.
    
    group_service = GroupService()
    dto: GroupMembersDTO = group_service.get_group_members(group)
    return jsonify(dto.model_dump())

@bp.post("/example22/groups")
@basic_auth
def create_group() -> Response | tuple[Response, int]:
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
def update_group(group: str) -> Response | tuple[Response, int]:
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


# ========== Organization Management ==========

@bp.post("/example22/organizations")
def register_organization() -> Response | tuple[Response, int]:
    """
    Register a new organization with its first user (owner).

    Accepts a POST request with a JSON body:
    {
        "org_name": "string",
        "domain": "string",
        "owner_email": "string",
        "owner_first_name": "string",
        "owner_last_name": "string",
        "owner_password": "string"
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"status": "error", "message": "No JSON data provided"}), 400

        # Create organization
        org_cmd = CreateOrganization(
            name=data["org_name"],
            domain=data["domain"],
            owner_email=data["owner_email"]
        )

        # Create the owner user
        user_cmd = CreateUser(
            email=data["owner_email"],
            first_name=data["owner_first_name"],
            last_name=data["owner_last_name"],
            password=data["owner_password"]
        )

    except (KeyError, ValidationError) as e:
        return jsonify({"status": "error", "message": f"Invalid input: {str(e)}"}), 400

    org_service = OrganizationService()
    user_service = UserService()

    try:
        # Check if domain already exists
        existing_org = org_service.organizations.get_by_domain(data["domain"])
        if existing_org:
            return jsonify({"status": "error", "message": "Organization domain already exists"}), 400

        # Check if user already exists
        existing_user = user_service.users.get_by_email(data["owner_email"])
        if existing_user:
            return jsonify({"status": "error", "message": "User email already exists"}), 400

        # Create organization and user
        org_dto = org_service.create_organization(org_cmd)
        user_dto = user_service.create_user(user_cmd)

        return jsonify({
            "status": "success",
            "organization": org_dto.model_dump(),
            "owner": user_dto.model_dump()
        })

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# ========== User Management ==========

@bp.post("/example22/users")
@basic_auth
def create_user() -> Response | tuple[Response, int]:
    """
    Create a new user. Only organization owners can create users in their domain.

    Accepts a POST request with a JSON body:
    {
        "email": "string",
        "first_name": "string",
        "last_name": "string",
        "password": "string"
    }
    """
    try:
        cmd = CreateUser.model_validate_json(request.data)
    except ValidationError as e:
        return jsonify({"status": "error", "message": str(e)}), 400

    user_service = UserService()
    org_service = OrganizationService()

    # Check if requester is org owner for the target domain
    target_domain = cmd.email.split('@')[-1]
    requester_domain = g.user.split('@')[-1]

    if target_domain != requester_domain:
        return jsonify({"status": "error", "message": "Can only create users in your organization domain"}), 403

    if not org_service.organizations.is_owner(target_domain, g.user):
        return jsonify({"status": "error", "message": "Only organization owners can create users"}), 403

    # Check if user or group already exists (cross-category uniqueness)
    existing_user = user_service.users.get_by_email(cmd.email)
    if existing_user:
        return jsonify({"status": "error", "message": "User already exists"}), 400

    group_service = GroupService()
    existing_group = group_service.groups.get_by_name(cmd.email)
    if existing_group:
        return jsonify({"status": "error", "message": "Name conflicts with existing group"}), 400

    try:
        dto = user_service.create_user(cmd)
        return jsonify(dto.model_dump())
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@bp.get("/example22/users/<user_email>")
@basic_auth
def get_user(user_email: str) -> Response | tuple[Response, int]:
    """Get user information. Users can see their own info, org owners can see users in their org."""
    user_service = UserService()
    org_service = OrganizationService()

    # Users can always see their own info
    if g.user == user_email:
        user = user_service.users.get_by_email(user_email)
        if not user:
            return jsonify({"status": "error", "message": "User not found"}), 404
        return jsonify(UserDTO.from_db(user).model_dump())

    # Check if requester is org owner for the target user's domain
    target_domain = user_email.split('@')[-1]
    if not org_service.organizations.is_owner(target_domain, g.user):
        return jsonify({"status": "error", "message": "Can only view users in your organization as owner"}), 403

    user = user_service.users.get_by_email(user_email)
    if not user:
        return jsonify({"status": "error", "message": "User not found"}), 404

    return jsonify(UserDTO.from_db(user).model_dump())


@bp.put("/example22/users/<user_email>")
@basic_auth
def update_user(user_email: str) -> Response | tuple[Response, int]:
    """
    Update user information. Users can update themselves, org owners can update users in their org.

    Accepts a PUT request with a JSON body:
    {
        "first_name": "string",
        "last_name": "string",
        "password": "string" (optional)
    }
    """
    user_service = UserService()
    org_service = OrganizationService()

    # Check authorization: user themselves OR org owner
    target_domain = user_email.split('@')[-1]
    is_self = g.user == user_email
    is_org_owner = org_service.organizations.is_owner(target_domain, g.user)

    if not is_self and not is_org_owner:
        return jsonify({"status": "error", "message": "Can only update yourself or users in your organization as owner"}), 403

    user = user_service.users.get_by_email(user_email)
    if not user:
        return jsonify({"status": "error", "message": "User not found"}), 404

    try:
        data = request.get_json()
        if not data:
            return jsonify({"status": "error", "message": "No JSON data provided"}), 400

        # Update basic fields
        if "first_name" in data:
            user.first_name = data["first_name"]
        if "last_name" in data:
            user.last_name = data["last_name"]
        if "password" in data:
            user.password_hash = bcrypt.hashpw(data["password"].encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

        user_service.s.flush()
        return jsonify(UserDTO.from_db(user).model_dump())

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@bp.delete("/example22/users/<user_email>")
@basic_auth
def delete_user(user_email: str) -> Response | tuple[Response, int]:
    """Delete user. Only organization owners can delete users (not themselves)."""
    user_service = UserService()
    org_service = OrganizationService()

    if g.user == user_email:
        return jsonify({"status": "error", "message": "Cannot delete yourself"}), 400

    target_domain = user_email.split('@')[-1]
    if not org_service.organizations.is_owner(target_domain, g.user):
        return jsonify({"status": "error", "message": "Only organization owners can delete users"}), 403

    user = user_service.users.get_by_email(user_email)
    if not user:
        return jsonify({"status": "error", "message": "User not found"}), 404

    try:
        user_service.s.delete(user)
        user_service.s.flush()
        return jsonify({"status": "success", "message": "User deleted"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# ========== Message Management ==========

@bp.get("/example22/users/<user_email>/messages")
@basic_auth
def get_user_messages(user_email: str) -> Response | tuple[Response, int]:
    """Get messages sent to a user. Users can only see their own messages."""
    if g.user != user_email:
        return jsonify({"status": "error", "message": "Can only view your own messages"}), 403

    message_service = MessageService()
    dto = message_service.get_user_messages(user_email)
    return jsonify(dto.model_dump())


@bp.post("/example22/users/<user_email>/messages")
@basic_auth
def send_user_message(user_email: str) -> Response | tuple[Response, int]:
    """
    Send message to a user.

    Accepts a POST request with a JSON body:
    {
        "message": "string"
    }
    """
    try:
        data = request.get_json()
        if not data or "message" not in data:
            return jsonify({"status": "error", "message": "Message content required"}), 400
    except Exception as e:
        return jsonify({"status": "error", "message": "Invalid JSON"}), 400

    message_service = MessageService()

    # Check if target user exists
    user_service = UserService()
    target_user = user_service.users.get_by_email(user_email)
    if not target_user:
        return jsonify({"status": "error", "message": "Target user not found"}), 404

    try:
        message_service.messages.send_to_user(g.user, user_email, data["message"])
        return jsonify({"status": "success", "message": "Message sent"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@bp.post("/example22/groups/<group>/messages")
@basic_auth
@check_group_membership
def send_group_message(group: str) -> Response | tuple[Response, int]:
    """
    Send message to a group. Must be a group member.

    Accepts a POST request with a JSON body:
    {
        "message": "string"
    }
    """
    try:
        data = request.get_json()
        if not data or "message" not in data:
            return jsonify({"status": "error", "message": "Message content required"}), 400
    except Exception as e:
        return jsonify({"status": "error", "message": "Invalid JSON"}), 400

    message_service = MessageService()

    try:
        message_service.messages.send_to_group(g.user, group, data["message"])
        return jsonify({"status": "success", "message": "Message sent"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# ========== Enhanced Group Management ==========

@bp.post("/example22/groups/create")
@basic_auth
def create_user_group() -> Response | tuple[Response, int]:
    """
    Create a new group with cross-category uniqueness check. Any user can create a group.

    Accepts a POST request with a JSON body:
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
        dto = group_service.create_group(g.user, cmd)
        return jsonify(dto.model_dump())
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
