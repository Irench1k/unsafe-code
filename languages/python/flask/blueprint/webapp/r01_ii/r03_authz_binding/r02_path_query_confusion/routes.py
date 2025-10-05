from flask import Blueprint, request, g
from .decorator import (
    basic_auth_v1, check_group_membership_v1,
    basic_auth_v2, check_group_membership_v2
)
from .database import get_user_messages, get_group_messages

bp = Blueprint("authz_path_query_confusion", __name__)


# @unsafe[block]
# id: 2
# title: "Authorization Binding Drift via Path-Query Confusion"
# notes: |
#   This example demonstrates authorization binding drift caused by a decorator
#   that merges path and query parameters with query-priority.
#
#   THE VULNERABILITY: Authorization binding drift, NOT source precedence.
#   - Authentication establishes WHO: Plankton (verified identity)
#   - Authorization checks WHICH resource: staff@chum-bucket.sea (from query param)
#   - Action accesses DIFFERENT resource: staff@krusty-krab.sea (from path param)
#
#   The key insight: We know WHO Plankton is (authentication succeeded), but
#   we allow him to control WHICH resource the authorization checks versus
#   WHICH resource gets accessed.
#
#   Attack flow:
#   1. Plankton authenticates as himself (WHO = plankton@chum-bucket.sea) ✓
#   2. Authorization decorator checks access to staff@chum-bucket.sea (query param) ✓
#   3. Handler retrieves messages from staff@krusty-krab.sea (path param) ✗
#
#   This is binding drift because the authenticated identity is correct, but
#   the resource identifier gets rebound between authorization and action.
# @/unsafe
@bp.get("/example2/groups/<group>/messages")
@basic_auth_v1
@check_group_membership_v1
def example2_group_messages(group):
    """Returns messages from a specified group."""
    return get_group_messages(group)


@bp.get("/example2/user/messages")
@basic_auth_v1
@check_group_membership_v1
def example2_user_messages():
    """Returns user's private messages, or group messages if specified."""
    if 'group' in request.args:
        return get_group_messages(request.args.get("group"))
    return get_user_messages(g.user)
# @/unsafe[block]


# @unsafe[block]
# id: 3
# title: "Authorization Binding Drift Despite Global Source of Truth"
# notes: |
#   This example attempts to fix the binding drift by introducing a single
#   source of truth (g.group), but the vulnerability persists because handlers
#   still use path parameters directly.
#
#   THE VULNERABILITY: Authorization binding drift via inconsistent source usage.
#   - Authentication establishes WHO: Plankton (stored in g.user) ✓
#   - Decorator sets g.group using query-priority merging ✓
#   - Authorization checks WHICH resource: g.group (staff@chum-bucket.sea from query) ✓
#   - Action accesses DIFFERENT resource: group parameter (staff@krusty-krab.sea from path) ✗
#
#   This demonstrates that even "single source of truth" patterns can fail if:
#   1. The source is populated with user-controlled priority logic
#   2. Some code paths ignore the source and use raw request data
#
#   Attack flow (same as Example 2):
#   1. Plankton authenticates as himself ✓
#   2. Decorator sets g.group = "staff@chum-bucket.sea" (query param) ✓
#   3. Authorization checks membership in g.group ✓
#   4. Handler uses path param "staff@krusty-krab.sea" instead of g.group ✗
#
#   The fix would be to either:
#   a) Always use g.group in handlers (never path params directly), OR
#   b) Don't set g.group with merging logic - use path param directly everywhere
# @/unsafe
@bp.get("/example3/groups/<group>/messages")
@basic_auth_v2
@check_group_membership_v2
def example3_group_messages(group):
    """Returns messages from a specified group."""
    return get_group_messages(group)


@bp.get("/example3/user/messages")
@basic_auth_v2
@check_group_membership_v2
def example3_user_messages():
    """Returns user's private messages, or group messages if specified."""
    if 'group' in request.args:
        return get_group_messages(g.group)
    return get_user_messages(g.user)
# @/unsafe[block]
