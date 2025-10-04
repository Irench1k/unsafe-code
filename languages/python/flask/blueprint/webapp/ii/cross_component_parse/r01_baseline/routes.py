from flask import Blueprint, request, g
from .decorator import basic_auth_v1
from .database import get_user_messages, get_group_messages, is_group_member

bp = Blueprint("baseline", __name__)

# @unsafe[block]
# id: 13
# title: "Shared Contract Baseline [Not Vulnerable]"
# notes: |
#   We move to authorization rather than authentication vulnerabilities, so
#   for the following examples the authentication will be done reliably and
#   safely, via the `Authorization` header (based on Basic Auth and handled
#   in the `@basic_auth_v1` decorator). We also follow the best practices by
#   storing the authenticated user in the global context (`g.user`).
#
#   Imagine that at this point we have many `/groups/` and `/user/` endpoints
#   for creating, updating and deleting groups, users and messages.
#
#   When the endpoint needs to work with a specific group, this could be
#   passed as a query/form argument as in the previous examples, but if
#   the `group` argument is required, it might be more idiomatic to make
#   it a path parameter instead.
#
#   Here we will work with two endpoints, the `/groups/<group>/messages` which
#   will return the messages from a specific group (taking the `group` from
#   the path) and the `/user/messages` which will return the user's private
#   messages by default, but also supporting an optional `group` query
#   argument.
# @/unsafe
@bp.get("/example13/groups/<group>/messages")
@basic_auth_v1
def example13_group_messages(group):
    """Returns group's messages, if the user is a member of the group."""
    if not is_group_member(g.user, group):
        return "Forbidden: not an member for the requested group", 403
    return get_group_messages(group)

@bp.get("/example13/user/messages")
@basic_auth_v1
def example13_user_messages():
    """
    Returns user's messages: private or from a group.

    By default provides the user's private messages, but if a `group` query
    argument is provided, it will return the messages from the specified group:

    /user/messages                              -> private messages of the logged in user
    /user/messages?group=staff@krusty-krab.sea  -> messages from the staff group, if the user is a member of the group
    """
    if 'group' not in request.args:
        return get_user_messages(g.user)

    group = request.args.get("group")
    if not is_group_member(g.user, group):
        return "Forbidden: not an member for the requested group", 403
    return get_group_messages(group)
# @/unsafe[block]
