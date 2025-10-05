from functools import wraps
from .database import authenticate_ex8

# Example 8 decorator
# @unsafe[block]
# id: 8
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
    def decorated_example8(*args, **kwargs):
        if not authenticate_ex8():
            return "Invalid user or password", 401
        return f(*args, **kwargs)

    return decorated_example8
# @/unsafe[block]
