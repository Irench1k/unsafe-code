from flask import request, Response, g
from functools import wraps
from .database import authenticate, is_group_member

def response_401():
    """Sends a 401 response, asking for authentication."""
    res = Response("Authentication required", 401,
                    headers={"WWW-Authenticate": "Basic realm='Authentication required'"})
    return res

def basic_auth(f):
    """Authenticates the user via Basic Auth. Stores the authenticated user in `g.user`."""
    @wraps(f)
    def decorated_basic_auth(*args, **kwargs):
        # request.authorization extracts the username and password from the Authorization header (Basic Auth)
        auth = request.authorization
        if not auth or not authenticate(auth.username, auth.password):
            return response_401()

        # Store the user in the global context
        g.user = auth.username
        return f(*args, **kwargs)

    return decorated_basic_auth

# @unsafe[block]
# id: 1
# part: 2
# @/unsafe
def check_group_membership(f):
    @wraps(f)
    def decorated_check_group_membership(*args, **kwargs):
        group = request.values.get("group")

        if group and not is_group_member(g.user, group):
            return "Forbidden: not an member for the requested group", 403

        return f(*args, **kwargs)
    return decorated_check_group_membership
# @/unsafe[block]
