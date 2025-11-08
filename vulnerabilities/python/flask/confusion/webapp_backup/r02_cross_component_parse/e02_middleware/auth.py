from .db import get_profile, profile_is_active


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
