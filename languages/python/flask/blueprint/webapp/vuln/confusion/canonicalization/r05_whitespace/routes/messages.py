from flask import Blueprint, Response, g, jsonify, request
from pydantic import ValidationError

from ..decorator import basic_auth, check_group_membership
from ..schemas.messages import MessagesDTO, SendMessageRequest
from ..services.messages import MessageService
from ..services.users import UserService

messages_bp = Blueprint("messages", __name__)

@messages_bp.get("/users/<user_email>")
@basic_auth
def get_user_messages(user_email: str) -> Response | tuple[Response, int]:
    """
    Get messages sent to a user. Users can only see their own messages.

    GET /messages/users/{user_email}
    """
    if g.user != user_email:
        return jsonify({"status": "error", "message": "Can only view your own messages"}), 403

    message_service = MessageService()
    dto: MessagesDTO = message_service.get_user_messages(user_email)
    return jsonify(dto.model_dump())


@messages_bp.post("/users/<user_email>")
@basic_auth
def send_user_message(user_email: str) -> Response | tuple[Response, int]:
    """
    Send message to a user.

    POST /messages/users/{user_email}

    Accepts a JSON body:
    {
        "message": "string"
    }
    """
    try:
        cmd = SendMessageRequest.model_validate_json(request.data)
    except ValidationError as e:
        return jsonify({"status": "error", "message": str(e)}), 400

    message_service = MessageService()

    # Check if target user exists
    user_service = UserService()
    target_user = user_service.users.get_by_email(user_email)
    if not target_user:
        return jsonify({"status": "error", "message": "Target user not found"}), 404

    try:
        message_service.messages.send_to_user(g.user, user_email, cmd.message)
        return jsonify({"status": "success", "message": "Message sent"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@messages_bp.get("/groups/<group>")
@basic_auth
@check_group_membership
def get_group_messages(group: str) -> Response | tuple[Response, int]:
    """
    Get messages sent to a group. Must be a group member.

    GET /messages/groups/{group}
    """
    message_service = MessageService()
    dto: MessagesDTO = message_service.get_group_messages(group)
    return jsonify(dto.model_dump())


@messages_bp.post("/groups/<group>")
@basic_auth
@check_group_membership
def send_group_message(group: str) -> Response | tuple[Response, int]:
    """
    Send message to a group. Must be a group member.

    POST /messages/groups/{group}

    Accepts a JSON body:
    {
        "message": "string"
    }
    """
    try:
        cmd = SendMessageRequest.model_validate_json(request.data)
    except ValidationError as e:
        return jsonify({"status": "error", "message": str(e)}), 400

    message_service = MessageService()

    try:
        message_service.messages.send_to_group(g.user, group, cmd.message)
        return jsonify({"status": "success", "message": "Message sent"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500