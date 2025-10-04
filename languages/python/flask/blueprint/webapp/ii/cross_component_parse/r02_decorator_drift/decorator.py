from flask import request, Response, g
from functools import wraps
from .database import authenticate_ex8, authenticate_ex14, is_group_member

def response_401():
    """Sends a 401 response, asking for authentication."""
    res = Response("Authentication required", 401,
                    headers={"WWW-Authenticate": "Basic realm='Authentication required'"})
    return res

# Example 8 decorator
# @unsafe[block]
# id: 8
# part: 2
# @/unsafe
def authentication_required(f):
    @wraps(f)
    def decorated_example8(*args, **kwargs):
        if not authenticate_ex8():
            return "Invalid user or password", 401
        return f(*args, **kwargs)

    return decorated_example8
# @/unsafe[block]


# Example 14 decorator
# @unsafe[block]
# id: 14
# part: 2
# @/unsafe
def basic_auth_v1(f):
    """Authenticates the user via Basic Auth. Stores the authenticated user in `g.user`."""
    @wraps(f)
    def decorated_basic_auth(*args, **kwargs):
        # request.authorization extracts the username and password from the Authorization header (Basic Auth)
        auth = request.authorization
        if not auth or not authenticate_ex14(auth.username, auth.password):
            return response_401()

        # Store the user in the global context
        g.user = auth.username
        return f(*args, **kwargs)

    return decorated_basic_auth


def check_group_membership_v1(f):
    @wraps(f)
    def decorated_check_group_membership(*args, **kwargs):
        group = request.args.get("group") or request.view_args.get("group")

        if group and not is_group_member(g.user, group):
            return "Forbidden: not an member for the requested group", 403

        return f(*args, **kwargs)
    return decorated_check_group_membership
# @/unsafe[block]

# Example 15 decorators
# @unsafe[block]
# id: 15
# part: 2
# @/unsafe
def basic_auth_v2(f):
    @wraps(f)
    def decorated_basic_auth(*args, **kwargs):
        auth = request.authorization
        if not auth or not authenticate_ex14(auth.username, auth.password):
            return response_401()

        # Store the user and group in the global context
        g.user = auth.username
        g.group = request.args.get("group") or request.view_args.get("group")
        return f(*args, **kwargs)
    return decorated_basic_auth

def check_group_membership_v2(f):
    @wraps(f)
    def decorated_check_group_membership(*args, **kwargs):
        if g.get("group", None) and not is_group_member(g.user, g.group):
            return "Forbidden: not an member for the requested group", 403

        return f(*args, **kwargs)
    return decorated_check_group_membership
# @/unsafe[block]
