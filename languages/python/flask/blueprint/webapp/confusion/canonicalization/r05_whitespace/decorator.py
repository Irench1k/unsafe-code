from functools import wraps

from flask import Response, g, request

from .services.groups import GroupService
from .services.users import UserService


def response_401():
    """Sends a 401 response, asking for authentication."""
    res = Response(
        "Authentication required",
        401,
        headers={"WWW-Authenticate": "Basic realm='Authentication required'"},
    )
    return res

def basic_auth(f):
    """Authenticates the user via Basic Auth. Stores the authenticated user in `g.user`."""
    @wraps(f)
    def decorated_basic_auth(*args, **kwargs):
        # request.authorization extracts the username and password from the Authorization header (Basic Auth)
        auth = request.authorization
        user_service = UserService()

        if not auth or not user_service.authenticate(auth.username, auth.password):
            return response_401()

        # Store the user in the global context
        g.user = auth.username
        return f(*args, **kwargs)

    return decorated_basic_auth

# @unsafe[block]
# id: 22
# part: 1
# @/unsafe
def check_group_membership(f):
    @wraps(f)
    def decorated_check_group_membership(*args, **kwargs):
        group = request.view_args.get("group")

        # Remove extra whitespaces that users can add due to autocompletion
        group_no_whitespace = group.strip()

        group_service = GroupService()

        if not group_service.is_member(g.user, group_no_whitespace):
            return "Forbidden: not an member for the requested group", 403

        return f(*args, **kwargs)

    return decorated_check_group_membership
# @/unsafe[block]

# @unsafe[block]
# id: 22
# part: 2
# @/unsafe
def check_if_admin(f):
    @wraps(f)
    def decorated_check_if_admin(*args, **kwargs):
        group = request.view_args.get("group")
        
        group_service = GroupService()

        if not group_service.is_admin(g.user, group):
            return "Forbidden: not an admin for the requested group", 403
        
        return f(*args, **kwargs)
     
    return decorated_check_if_admin
# @/unsafe[block]