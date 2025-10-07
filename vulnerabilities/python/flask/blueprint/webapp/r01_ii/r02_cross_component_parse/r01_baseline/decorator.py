from flask import request
from functools import wraps
from .database import authenticate

# @unsafe[block]
# id: 1
# part: 2
# @/unsafe
def authentication_required(f):
    """
    Authenticates the user via query parameters.

    This decorator consistently sources both username and password from
    request.args, matching the source used by the handler.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = request.args.get("user")
        password = request.args.get("password")

        if not authenticate(user, password):
            return "Authentication required", 401

        return f(*args, **kwargs)

    return decorated_function
# @/unsafe[block]
