from flask import Blueprint, Response, jsonify, request
from pydantic import ValidationError

from ..schemas.organizations import RegisterOrganizationRequest, OrganizationDTO
from ..schemas.users import CreateUser, UserDTO
from ..services.organizations import OrganizationService
from ..services.users import UserService

organizations_bp = Blueprint("organizations", __name__)

@organizations_bp.post("/")
def register_organization() -> Response | tuple[Response, int]:
    """
    Register a new organization with its first user (owner).

    POST /organizations

    Accepts a JSON body:
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
        cmd = RegisterOrganizationRequest.model_validate_json(request.data)
    except ValidationError as e:
        return jsonify({"status": "error", "message": str(e)}), 400

    org_service = OrganizationService()
    user_service = UserService()

    try:
        # Check if domain already exists
        existing_org = org_service.organizations.get_by_domain(cmd.domain)
        if existing_org:
            return jsonify({"status": "error", "message": "Organization domain already exists"}), 400

        # Check if user already exists
        existing_user = user_service.users.get_by_email(cmd.owner_email)
        if existing_user:
            return jsonify({"status": "error", "message": "User email already exists"}), 400

        # Create organization command
        from ..schemas.organizations import CreateOrganization
        org_cmd = CreateOrganization(
            name=cmd.org_name,
            domain=cmd.domain,
            owner_email=cmd.owner_email
        )

        # Create the owner user command
        user_cmd = CreateUser(
            email=cmd.owner_email,
            first_name=cmd.owner_first_name,
            last_name=cmd.owner_last_name,
            password=cmd.owner_password
        )

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