from flask import Blueprint, request, g
from .decorator import basic_auth_v1, check_group_membership_v1, basic_auth_v2, check_group_membership_v2, basic_auth_v3
from .database import get_user_messages, get_group_messages, is_group_member

bp = Blueprint("behavior_order", __name__)

# @unsafe[block]
# id: 13
# title: "Motivation for using path and query parameters [Not Vulnerable]"
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


# @unsafe[block]
# id: 14
# title: "Path and query parameter confusion via merging decorator"
# notes: |
#   Here we aim to make the code more idiomatic by moving the group membership
#   check to the decorator `@check_group_membership`. It results in a cleaner
#   code and appears to confirm to the single-responsibility principle.
#
#   This code, however, is now vulnerable to path and query parameter confusion.
# @/unsafe
@bp.get("/example14/groups/<group>/messages")
@basic_auth_v1
@check_group_membership_v1
def example14_group_messages(group):
    """Returns group's messages, if the user is a member of the group."""
    return get_group_messages(group)

@bp.get("/example14/user/messages")
@basic_auth_v1
@check_group_membership_v1
def example14_user_messages():
    """Returns user's messages: private or from a group."""
    if 'group' in request.args:
        return get_group_messages(request.args.get("group"))
    return get_user_messages(g.user)
# @/unsafe[block]


# @unsafe[block]
# id: 15
# title: "Path and query parameter confusion despite global source of truth"
# notes: |
#   Here we aim to mitigate the confusion risk in the `group` merging behavior
#   by applying the single source of truth. We do this already for the identity
#   of the authenticated user, by storing it in the global context (`g.user`).
#   So, here we extend `@basic_auth_v2` to also store the group in the global
#   context (`g.group`).
#
#   Despite these efforts, the code is still vulnerable.
# @/unsafe
@bp.get("/example15/groups/<group>/messages")
@basic_auth_v2
@check_group_membership_v2
def example15_group_messages(group):
    """Returns group's messages, if the user is a member of the group."""
    return get_group_messages(group)

@bp.get("/example15/user/messages")
@basic_auth_v2
@check_group_membership_v2
def example15_user_messages():
    """Returns user's messages: private or from a group."""
    if 'group' in request.args:
        return get_group_messages(g.group)  # We use g.group here now, single source of truth
    return get_user_messages(g.user)
# @/unsafe[block]


# @unsafe[block]
# id: 16
# title: "Path and query parameter confusion due to decorator order"
# notes: |
#   We try to fix the root cause of the vulnerability here by enforcing correct
#   merging order – view args take precedence over query args. Additionally, we
#   enforce that only one of the two can be present.
#
#   The code, however, remains vulnerable despite these efforts! This time, the
#   problem is that the `@check_group_membership_v2` decorator is applied too
#   early – before the `@basic_auth_v3` decorator which is responsible for setting
#   the `g.group` global variable. This makes `@check_group_membership_v2` a no-op.
# @/unsafe
@bp.get("/example16/groups/<group>/messages")
@check_group_membership_v2
@basic_auth_v3
def example16_group_messages(group):
    """Returns group's messages, if the user is a member of the group."""
    return get_group_messages(group)
# @/unsafe[block]
