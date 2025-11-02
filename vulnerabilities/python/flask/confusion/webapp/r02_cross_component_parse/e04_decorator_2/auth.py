from functools import wraps

from flask import g, jsonify, request

from .db import authenticate, get_profile, profile_is_active


# @unsafe[block]
# id: 4
# part: 2
# @/unsafe
def require_auth(f):
    """Authentication decorator."""

    @wraps(f)
    def decorated(*args, **kwargs):
        # Security Fix! Don't use `request.values` here please, it is insecure.
        user = request.form.get("user")
        password = request.form.get("password")

        if not authenticate(user, password):
            return jsonify({"error": "Invalid credentials"}), 401

        # Store authenticated user in g
        g.user = user

        return f(*args, **kwargs)

    return decorated


# @/unsafe[block]


def cross_account_access_control(username):
    """Cross-account access control."""
    if not username:
        raise ValueError("Username required")

    # Fetch profile to verify that the user exists
    profile = get_profile(username)
    if not profile:
        raise ValueError("User not found")

    # Prevent incomplete profiles from being shown by checking for completed onboarding
    if not profile_is_active(username, profile):
        raise ValueError("Username does not match profile")
