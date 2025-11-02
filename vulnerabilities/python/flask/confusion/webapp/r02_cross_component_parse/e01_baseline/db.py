"""Database operations for baseline example."""

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


def get_messages(user):
    """Retrieves all messages for a user."""
    return db["messages"].get(user, [])


def create_message(sender, recipient, text):
    """Creates a new message."""
    msg_id = db["next_message_id"]
    db["next_message_id"] += 1

    message = {"id": msg_id, "from": sender, "text": text, "read": False}

    if recipient not in db["messages"]:
        db["messages"][recipient] = []

    db["messages"][recipient].append(message)
    return msg_id


def get_profile(user, internal=False):
    """Gets a user's profile."""
    user = sanitize_username(user)

    raw_profile = db["profiles"].get(user)
    if internal:
        return raw_profile

    profile = raw_profile.copy()
    profile["username"] = user
    return profile


def update_profile(user, display_name=None, bio=None):
    """Updates a user's profile."""
    profile = get_profile(user, internal=True)

    if display_name:
        profile["display_name"] = display_name
    if bio:
        profile["bio"] = bio

    return True


def profile_is_active(username, profile):
    """Check if the profile passed onboarding process and can be shown to other users."""
    try:
        # Check that the password has been set
        if not profile["password"]:
            return False

        # Check that at least one message has been received
        print("Checking if messages are present for", username)
        if not len(db["messages"][username]) > 0:
            print("No messages found for", username)
            return False
    except Exception as e:
        print("Error checking if messages are present for", username, e)
        raise Exception(
            f"Something went wrong when checking if {username} is active: {profile}"
        ) from e

    print("All checks passed for", username)

    # The user is active if all checks pass without errors
    return True
