from .db import db


def messages_get(user):
    """Retrieves all messages for the specified user."""
    messages = db["messages"].get(user, [])
    return {"mailbox": user, "messages": messages}


def messages_delete(user, index, count):
    """Deletes messages for the specified user."""
    deleted_messages = 0

    messages = db["messages"].get(user, [])
    if index < 0 or index >= len(messages):
        return 0
    for i in range(index, index + count):
        if i >= len(messages):
            break
        del messages[i]
        deleted_messages += 1
    return deleted_messages
