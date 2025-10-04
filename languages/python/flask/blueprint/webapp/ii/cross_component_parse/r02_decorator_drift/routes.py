from flask import Blueprint, request, g
from .decorator import authentication_required, basic_auth_v1, check_group_membership_v1, basic_auth_v2, check_group_membership_v2
from .database import get_messages_ex8, get_user_ex8, get_user_messages, get_group_messages, is_group_member

bp = Blueprint("decorator_drift", __name__)

# @unsafe[block]
# id: 8
# title: "Decorator-based Authentication with Parsing Drift"
# notes: |
#   Shows how using decorators can obscure parameter source confusion.
#
#   Example 8 is functionally equivalent to Example 4 from the old parameter source
#   confusion examples, but it may be harder to spot the vulnerability while using decorators.
#
#   The decorator authenticates using request.args.get("user"), but the handler retrieves
#   the user via get_user() which prioritizes request.form over request.args.
# @/unsafe
@bp.route("/example8", methods=["GET", "POST"])
@authentication_required
def example8():
    messages = get_messages_ex8(get_user_ex8())
    if messages is None:
        return "No messages found", 404
    return messages
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
#   The decorator's merging logic (request.args or request.view_args) prioritizes
#   query parameters, while Flask's URL routing binds path parameters directly to
#   function arguments. An attacker can pass their group in the query string to
#   bypass authorization while accessing a different group's data via the path.
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
#   Despite these efforts, the code is still vulnerable. The decorator sets g.group
#   with query-priority merging, but the handler function still receives the path
#   parameter directly from Flask's routing. The handler passes this path parameter
#   to get_group_messages(), ignoring g.group entirely in example15_group_messages.
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
