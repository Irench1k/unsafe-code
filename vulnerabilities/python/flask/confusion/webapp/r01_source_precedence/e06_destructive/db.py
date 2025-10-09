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


def delete_message(user, index):
    """Removes a message from the specified user's inbox."""
    messages = db["messages"].get(user, None)
    if messages is None or index < 0 or index >= len(messages):
        return False
    del messages[index]
    return True
