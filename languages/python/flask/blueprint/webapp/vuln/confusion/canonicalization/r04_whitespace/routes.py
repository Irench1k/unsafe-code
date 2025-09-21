from flask import Blueprint, request, jsonify

from pydantic import ValidationError

from .decorator import basic_auth, check_group_membership, check_if_admin
from .database import get_group_messages, create_new_group, update_existing_group, group_exists
from .database.models import Group

bp = Blueprint("whitespace_2", __name__)

@bp.get("/example21/groups/<group>/messages")
@basic_auth
@check_group_membership
def example21(group):
    messages = get_group_messages(group)
    
    return jsonify([m.model_dump() for m in messages])

# @unsafe[block]
# id: 21
# title: Whitespace Canonicalization
# notes: |
#   Previously we only had 'add group' functionality. Now we add group update handler
#   as well. There are two distinct API endpoints now, one creates a new group (and we
#   make sure to check that the group truly does not exist yet!), and the other endpoint
#   updates the existing group (this is privileged operation, so we check that the user
#   is an admin with @check_if_admin decorator).
#
#   Unfortunately, the code remains vulnerable to canonicalization confusion attack. In the `create_group`
#   handler we perform group uniqueness check on the raw group name provided by user `request.json.get("name")`.
#   However, if the check passes, the `create_new_group` is called with the canonicalized data in the Group
#   object. Group model uses `constr` feature from pydantic, which strips whitespace on insertion, so the
#   attacker can bypass group uniqueness check by providing a group name with extra whitespace at the start
#   or end of the group name.
#
#   Compare the exploit to exploit-19.http. Here the impact is much worse, because instead of ovewriting
#   the existing group (and losing its message history), this time Plankton can simply add himself to the
#   group admins, getting privileged access to existing group and its messages. This happens because
#   DatabaseStorage.add_group_to_storage tries to be idempotent and cleverly creates a new group if it
#   doesn't exist yet while only updating permissions of an existing group. As a result, even though
#   `create_group` and `update_group` are meant to be separate handlers, in fact they only differ in the
#   security check implementations, while the downstream code path is shared. So by bypassing group
#   uniqueness check in `create_group` Plankton in fact manages to use this handler as if it was
#   `update_group` - while he wouldn't be able to use `update_group` directly.
#
#   The root cause of the attack is again an inconsistent canonicalization: when we check for group existence,
#   we use raw input, but when we store the group, we use canonicalized data.
# @/unsafe
@bp.post("/example21/groups/new")
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

@bp.post("/example21/groups/<group>")
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
# @/unsafe[block]
