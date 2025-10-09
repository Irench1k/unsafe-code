from ..db import db  # Import shared database


# @unsafe[block]
# id: 4
# title: Cross-Module Parameter Source Confusion
# part: 1
# notes: |
#   In the previous example, you can still see that the `user` value gets retrieved from the
#   `request.args` during validation but from the `request.form` during data retrieval.
#
#   A more subtle example, where this is not immediately obvious (imagine, `authenticate_user`
#   is defined in an another file altogether):
# @/unsafe
def authenticate(user, password):
    """Validates user credentials against the database."""
    return password is not None and password == db["passwords"].get(user, None)


def get_messages(user):
    """Retrieves all messages for the specified user."""
    messages = db["messages"].get(user, None)
    if messages is None:
        return None
    return {"owner": user, "messages": messages}

# @/unsafe[block]
