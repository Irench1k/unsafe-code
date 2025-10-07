from flask import request, Response, g
from functools import wraps
from .database import authenticate, is_group_member

def response_401():
    """Sends a 401 response, asking for authentication."""
    res = Response("Authentication required", 401,
                    headers={"WWW-Authenticate": "Basic realm='Authentication required'"})
    return res

# @unsafe[block]
# id: 1
# part: 2
# @/unsafe
def basic_auth_v3(f):
    @wraps(f)
    def decorated_basic_auth(*args, **kwargs):
        auth = request.authorization
        if not auth or not authenticate(auth.username, auth.password):
            return response_401()

        # Store the user and group in the global context
        g.user = auth.username

        # Due to the string of past vulnerabilities, we take a very defensive approach here.
        # We explicitly check for the case where multiple parameters are present and stop
        # execution early. When merging, the view args take precedence over the query args.
        # In the handlers, always access the group from the global context (`g.group`)!
        group_from_view = request.view_args.get("group")
        group_from_query = request.args.get("group")
        if group_from_view and group_from_query:
            return "Illegal arguments", 400
        g.group = group_from_view or group_from_query

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
