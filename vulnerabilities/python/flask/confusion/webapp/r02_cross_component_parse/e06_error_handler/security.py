def sanitize_profile(profile):
    """Removes sensitive fields from profile."""
    if not profile:
        return None

    safe_profile = profile.copy()
    safe_profile.pop("password", None)
    return safe_profile


# @unsafe[block]
# id: 6
# part: 5
# @/unsafe
def sanitize_username(username):
    """Normalize and remove all suspicious characters from the username."""
    import re

    if not username:
        raise ValueError("Username required")

    return re.sub(r"[^a-zA-Z0-9]", "", username.lower())


# @/unsafe[block]
