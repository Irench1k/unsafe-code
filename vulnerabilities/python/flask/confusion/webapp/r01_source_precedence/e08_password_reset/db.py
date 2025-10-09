from ..db import db


def authenticate(user, password):
    """Validates user credentials against the database."""
    return password is not None and password == db["passwords"].get(user, None)


def get_messages(user):
    """Retrieves all messages for the specified user."""
    messages = db["messages"].get(user, None)
    if messages is None:
        return None
    return {"owner": user, "messages": messages}


def reset_password(user, new_password):
    """Updates the user's password in the database."""
    if user not in db["passwords"]:
        return False
    db["passwords"][user] = new_password
    return True
