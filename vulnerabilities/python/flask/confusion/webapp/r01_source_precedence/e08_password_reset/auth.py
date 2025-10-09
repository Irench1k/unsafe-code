from flask import request

from .db import authenticate


def authenticate_user():
    """
    Authenticates the user using unified parameter resolution.

    Merges query and form parameters to support flexible authentication flows.
    """
    return authenticate(
        request.values.get("user", None), request.values.get("password", None)
    )
