from flask import request, Response, g
from functools import wraps
from .database import authenticate


def response_401():
    """Sends a 401 response, asking for Basic authentication."""
    res = Response(
        "Authentication required",
        401,
        headers={"WWW-Authenticate": "Basic realm='Authentication required'"}
    )
    return res


# @unsafe[block]
# id: 13
# part: 2
# @/unsafe
def basic_auth_v1(f):
    """
    Authenticates the user via Basic Auth.
    Stores the authenticated user in `g.user`.
    """
    @wraps(f)
    def decorated_basic_auth(*args, **kwargs):
        # request.authorization extracts the username and password from the Authorization header (Basic Auth)
        auth = request.authorization
        if not auth or not authenticate(auth.username, auth.password):
            return response_401()

        # Store the authenticated user in the global context
        g.user = auth.username
        return f(*args, **kwargs)

    return decorated_basic_auth
# @/unsafe[block]
