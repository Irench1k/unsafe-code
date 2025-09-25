import bcrypt
from flask import Blueprint, Response, g, jsonify, request
from pydantic import ValidationError

from ..decorator import basic_auth
from ..schemas.users import CreateUser, UpdateUserRequest, UserDTO, UserModel
from ..services.organizations import OrganizationService
from ..services.users import UserService

users_bp = Blueprint("users", __name__)

@users_bp.post("/")
@basic_auth
def create_user() -> Response | tuple[Response, int]:
    """
    Create a new user. Only organization owners can create users in their domain.

    POST /users

    Accepts a JSON body:
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

    from ..services.groups import GroupService
    group_service = GroupService()
    existing_group = group_service.groups.get_by_name(cmd.email)
    if existing_group:
        return jsonify({"status": "error", "message": "Name conflicts with existing group"}), 400

    try:
        dto: UserDTO = user_service.create_user(cmd)
        return jsonify(dto.model_dump())
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@users_bp.get("/<user_email>")
@basic_auth
def get_user(user_email: str) -> Response | tuple[Response, int]:
    """
    Get user information. Users can see their own info, org owners can see users in their org.

    GET /users/{user_email}
    """
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

    user: UserModel | None = user_service.users.get_by_email(user_email)
    if not user:
        return jsonify({"status": "error", "message": "User not found"}), 404

    return jsonify(UserDTO.from_db(user).model_dump())


@users_bp.patch("/<user_email>")
@basic_auth
def update_user(user_email: str) -> Response | tuple[Response, int]:
    """
    Update user information. Users can update themselves, org owners can update users in their org.

    PATCH /users/{user_email}

    Accepts a JSON body:
    {
        "first_name": "string",
        "last_name": "string",
        "password": "string"
    }
    """
    try:
        cmd = UpdateUserRequest.model_validate_json(request.data)
    except ValidationError as e:
        return jsonify({"status": "error", "message": str(e)}), 400

    user_service = UserService()
    org_service = OrganizationService()

    # Check authorization: user themselves OR org owner
    target_domain = user_email.split('@')[-1]
    is_self = g.user == user_email
    is_org_owner = org_service.organizations.is_owner(target_domain, g.user)

    if not is_self and not is_org_owner:
        return jsonify({"status": "error", "message": "Can only update yourself or users in your organization as owner"}), 403

    user: UserModel | None = user_service.users.get_by_email(user_email)
    if not user:
        return jsonify({"status": "error", "message": "User not found"}), 404

    try:
        # Update basic fields
        if cmd.first_name is not None:
            user.first_name = cmd.first_name
        if cmd.last_name is not None:
            user.last_name = cmd.last_name
        if cmd.password is not None:
            user.password_hash = bcrypt.hashpw(cmd.password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

        user_service.s.flush()
        return jsonify(UserDTO.from_db(user).model_dump())

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@users_bp.delete("/<user_email>")
@basic_auth
def delete_user(user_email: str) -> Response | tuple[Response, int]:
    """
    Delete user. Only organization owners can delete users (not themselves).

    DELETE /users/{user_email}
    """
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