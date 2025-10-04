from flask import Blueprint, request, g
from .decorator import basic_auth_v1
from .database import get_user_messages, get_group_messages, is_group_member

bp = Blueprint("authz_baseline", __name__)

# @unsafe[block]
# id: 13
# title: "Secure Authorization Binding Baseline [Not Vulnerable]"
# notes: |
#   This demonstrates the correct way to handle authorization binding in a multi-user
#   application. Authentication establishes WHO the user is, and authorization checks
#   verify that the authenticated identity has access to the requested resource.
#
#   Key security properties:
#   - Authentication via Basic Auth establishes `g.user` (WHO)
#   - Authorization checks use the SAME source for the resource identifier (group parameter)
#   - The data retrieval also uses the SAME source for the resource identifier
#   - No user-controlled parameters can rebind the resource after authorization
#
#   This example provides two endpoints:
#   1. `/groups/<group>/messages` - Returns messages from a specific group (path parameter)
#   2. `/user/messages` - Returns user's private messages, or group messages if `group` query param provided
#
#   In both cases, the authorization check and the data access use the same source,
#   preventing any binding drift attacks.
# @/unsafe
@bp.get("/example13/groups/<group>/messages")
@basic_auth_v1
def example13_group_messages(group):
    """Returns messages from a specified group."""
    if not is_group_member(g.user, group):
        return "Forbidden: not a member of the requested group", 403

    return get_group_messages(group)


@bp.get("/example13/user/messages")
@basic_auth_v1
def example13_user_messages():
    """
    Returns user's private messages, or group messages if specified.

    Query parameters:
      - group (optional): Group identifier to retrieve messages from

    Examples:
      GET /user/messages                              → private messages
      GET /user/messages?group=staff@krusty-krab.sea  → group messages
    """
    if 'group' not in request.args:
        return get_user_messages(g.user)

    group = request.args.get("group")
    if not is_group_member(g.user, group):
        return "Forbidden: not a member of the requested group", 403

    return get_group_messages(group)
# @/unsafe[block]
