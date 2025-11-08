from ..db import db  # Import shared database


# @unsafe[block]
# id: 4
# part: 3
# @/unsafe
def authenticate(user, password):
    """Validates user credentials against the database."""
    return password and password == db["passwords"].get(user)


def messages_get(user):
    """Retrieves all messages for the specified user."""
    messages = db["messages"].get(user, [])
    return {"mailbox": user, "messages": messages}
# @/unsafe[block]
