from flask import Blueprint, request

from .auth import authenticate_user
from .db import messages_get, password_update

bp = Blueprint("source_precedence_request_values", __name__, url_prefix="/example7")


# @unsafe[block]
# id: 7
# part: 1
# title: Flask's request.values Precedence Rules
# notes: |
#   This example is functionally equivalent to example 5, except here we use built-in
#   `request.values` instead of writing our own source merging function.
#
#   This version of `authenticate_user` relies on `request.form` and is secure on its own,
#   but the vulnerability arises when `get_messages` uses `request.values` instead.
# @/unsafe
@bp.post("/users/me/messages")
def list_messages():
    """
    Retrieves messages for an authenticated user.

    Example request:
      POST /users/me/messages
      Content-Type: application/x-www-form-urlencoded

      user=mr.krabs&password=money
    """
    if not authenticate_user():
        return "Invalid user or password", 401

    return messages_get(request.values.get("user"))


# @/unsafe[block]


@bp.patch("/users/me/password")
def change_password():
    """
    Updates a user's password.

    Example request:
      PATCH /users/me/password
      Content-Type: application/x-www-form-urlencoded

      user=mr.krabs&password=money&new_password=new_password
    """
    if not authenticate_user():
        return "Invalid user or password", 401

    target_user = request.form.get("user")
    new_password = request.form.get("new_password")

    if not target_user or not new_password:
        return "Missing required parameters", 400

    if password_update(target_user, new_password):
        return {"status": "success", "user": target_user, "message": "Password updated"}
    else:
        return "User not found", 404
