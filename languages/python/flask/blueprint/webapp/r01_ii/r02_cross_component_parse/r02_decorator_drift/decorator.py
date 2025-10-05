from functools import wraps
from .database import authenticate_ex2

# Example 2 decorator
# @unsafe[block]
# id: 2
# part: 2
# @/unsafe
def authentication_required(f):
    """
    Authentication decorator that validates user credentials from query parameters.

    VULNERABILITY: This decorator only checks credentials from request.args,
    but the handler may retrieve the user identity from a different source,
    creating an authentication bypass via source precedence confusion.
    """
    @wraps(f)
    def decorated_example2(*args, **kwargs):
        if not authenticate_ex2():
            return "Invalid user or password", 401
        return f(*args, **kwargs)

    return decorated_example2
# @/unsafe[block]
