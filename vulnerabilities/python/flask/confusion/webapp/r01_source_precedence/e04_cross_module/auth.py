from flask import request

from .db import authenticate


# @unsafe[block]
# id: 4
# part: 2
# @/unsafe
def authenticate_user():
    """
    Authenticates the current user using form body credentials.

    Designed for POST-based authentication flows where credentials are in the request body,
    following security best practices to keep passwords out of URL logs.
    """
    return authenticate(request.form.get("user"), request.form.get("password"))
# @/unsafe[block]
