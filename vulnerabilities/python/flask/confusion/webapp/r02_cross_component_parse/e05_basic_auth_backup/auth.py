from functools import wraps

from flask import g, request

from .db import authenticate, get_profile, profile_is_active


def require_auth(f):
    """
    Authentication decorator using HTTP Basic Authentication.

    Extracts credentials from Authorization header, validates them, and stores
    authenticated user in g.user for handler use.
    """

    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth:
            return {"error": "Authentication required"}, 401

        if not authenticate(auth.username, auth.password):
            return {"error": "Invalid credentials"}, 401

        # Store authenticated user in g
        g.user = auth.username

        return f(*args, **kwargs)

    return decorated


def cross_account_access_control(username):
    """Cross-account access control."""
    if not username:
        raise ValueError("Username required")

    # Fetch profile to verify that the user exists
    profile = get_profile()
    if not profile:
        raise ValueError("User not found")

    # Prevent incomplete profiles from being shown by checking for completed onboarding
    if not profile_is_active(username, profile):
        raise ValueError("Username does not match profile")
