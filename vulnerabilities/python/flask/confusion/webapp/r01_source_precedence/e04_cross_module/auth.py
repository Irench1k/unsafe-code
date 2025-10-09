from flask import request

from .db import authenticate


# @unsafe[block]
# id: 4
# part: 2
# @/unsafe
def authenticate_user():
    """
    Authenticates the current user using query string credentials.

    Designed for GET-based authentication flows where credentials are passed in the URL.
    """
    return authenticate(
        request.args.get("user", None), request.args.get("password", None)
    )

# @/unsafe[block]
