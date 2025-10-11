from flask import request

from .db import authenticate


# @unsafe[block]
# id: 8
# part: 2
# @/unsafe
def authenticate_user():
    """
    Authenticates the user using form-based credentials.

    Designed for POST-based form submissions where credentials are in the request body.
    """
    return authenticate(request.values.get("user"), request.values.get("password"))


# @/unsafe[block]
