from hmac import compare_digest

from flask import request

from .database import get_api_key, get_user


def _authenticate(user, password):
    """Authenticates the user using the database."""
    # FIXME: add password hashing
    return compare_digest(user.password, password)


def _is_api_key_valid(api_key):
    """Validates the API key using the database."""
    if not api_key:
        return False

    correct_api_key = get_api_key()
    return compare_digest(api_key, correct_api_key)


def get_authenticated_user():
    """Gets the authenticated user from the request (Basic Auth only at this point)."""
    if not request.authorization:
        return None

    username = request.authorization.username
    password = request.authorization.password

    if not username or not password:
        return None

    user = get_user(username)
    if not user:
        return None

    if not _authenticate(user, password):
        return None

    return user


def validate_api_key():
    """Validates the API key from the request."""
    api_key = request.headers.get("X-API-Key")
    if not api_key:
        return False

    return _is_api_key_valid(api_key)
