from flask import request, Response, g
from functools import wraps
from .database import authenticate, is_group_member


def response_401():
    """Sends a 401 response, asking for Basic authentication."""
    res = Response(
        "Authentication required",
        401,
        headers={"WWW-Authenticate": "Basic realm='Authentication required'"}
    )
    return res


# Example 14 decorators
# @unsafe[block]
# id: 14
# part: 2
# @/unsafe
def basic_auth_v1(f):
    """Authenticates the user via Basic Auth, stores identity in g.user."""
    @wraps(f)
    def decorated_basic_auth(*args, **kwargs):
        auth = request.authorization
        if not auth or not authenticate(auth.username, auth.password):
            return response_401()

        g.user = auth.username
        return f(*args, **kwargs)

    return decorated_basic_auth


def check_group_membership_v1(f):
    """
    Checks if the authenticated user is a member of the requested group.

    Supports flexible group parameter passing via query string or path.
    """
    @wraps(f)
    def decorated_check_group_membership(*args, **kwargs):
        # Support both query and path parameters for group identifier
        group = request.args.get("group") or request.view_args.get("group")

        if group and not is_group_member(g.user, group):
            return "Forbidden: not a member of the requested group", 403

        return f(*args, **kwargs)
    return decorated_check_group_membership
# @/unsafe[block]


# Example 15 decorators
# @unsafe[block]
# id: 15
# part: 2
# @/unsafe
def basic_auth_v2(f):
    """
    Authenticates user via Basic Auth and establishes single source of truth.

    Stores both user and group identifiers in global context (g.user, g.group)
    to ensure consistent access across all decorators and handlers.
    """
    @wraps(f)
    def decorated_basic_auth(*args, **kwargs):
        auth = request.authorization
        if not auth or not authenticate(auth.username, auth.password):
            return response_401()

        g.user = auth.username
        # Establish single source of truth for group identifier
        g.group = request.args.get("group") or request.view_args.get("group")
        return f(*args, **kwargs)
    return decorated_basic_auth


def check_group_membership_v2(f):
    """
    Checks group membership using g.group from global context.

    Relies on basic_auth_v2 decorator to populate g.group with the
    canonical group identifier for consistent authorization checks.
    """
    @wraps(f)
    def decorated_check_group_membership(*args, **kwargs):
        if g.get("group", None) and not is_group_member(g.user, g.group):
            return "Forbidden: not a member of the requested group", 403

        return f(*args, **kwargs)
    return decorated_check_group_membership
# @/unsafe[block]
