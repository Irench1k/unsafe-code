from functools import wraps
from hmac import compare_digest

from flask import g, jsonify, request

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


def customer_authentication_required(f):
    """Authenticate customers via Basic Auth."""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = get_authenticated_user()
        if not user:
            return jsonify({"error": "User authentication required"}), 401
        g.user = user
        return f(*args, **kwargs)

    return decorated_function


def restaurant_manager_authentication_required(f):
    """Authenticate restaurant managers via API key."""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not validate_api_key():
            return jsonify({"error": "Restaurant manager authentication required"}), 401
        return f(*args, **kwargs)

    return decorated_function
