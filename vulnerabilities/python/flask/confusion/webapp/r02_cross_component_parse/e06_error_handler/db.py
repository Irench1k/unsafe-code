"""Database operations for error handler example."""

from ..db import db
from .security import sanitize_username


def authenticate(user, password):
    """Validates user credentials."""
    if not user or not password:
        return False

    profile = db["profiles"].get(user)
    if not profile:
        return False

    return profile["password"] == password


def get_profile(internal=False):
    """Gets a user's profile from DB (mutable if internal)"""
    from flask import g, request

    # This is meant for /profile/<username>/ endpoints which are explicitly meant
    # for accessing other users' profiles - so we prioritize view_args over g.user here
    user = sanitize_username(request.view_args.get("username") or g.user)

    raw_profile = db["profiles"].get(user)
    if internal:
        return raw_profile

    profile = raw_profile.copy()
    profile["username"] = user
    return profile


def profile_is_active(username, profile):
    """Check if the profile passed onboarding process and can be shown to other users."""
    try:
        # Check that the password has been set
        if not profile["password"]:
            return False

        # Check that at least one message has been received
        if not len(db["messages"][username]) > 0:
            return False
    except Exception as e:
        raise Exception(
            f"Something went wrong when checking if {username} is active: {profile}"
        ) from e

    # The user is active if all checks pass without errors
    return True
