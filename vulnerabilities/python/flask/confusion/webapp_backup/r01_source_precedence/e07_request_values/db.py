from ..db import db


def authenticate(user, password):
    """Validates user credentials against the database."""
    return password and password == db["passwords"].get(user)


def messages_get(user):
    """Retrieves all messages for the specified user."""
    messages = db["messages"].get(user, [])
    return {"mailbox": user, "messages": messages}


def password_update(user, new_password):
    """Updates the user's password in the database."""
    if user not in db["passwords"]:
        return False
    db["passwords"][user] = new_password
    return True
