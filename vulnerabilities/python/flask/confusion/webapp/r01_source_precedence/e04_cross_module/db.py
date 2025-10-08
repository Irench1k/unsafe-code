from flask import request

db = {
    "passwords": {
        "spongebob": "bikinibottom",
        "squidward": "clarinet123",
        "plankton": "chumbucket",
        "mr.krabs": "money",
    },
    "messages": {
        "spongebob": [
            {"from": "patrick", "message": "SpongeBob! I'm ready! I'm ready! Let's go jellyfishing!"},
        ],
        "squidward": [
            {
                "from": "mr.krabs",
                "message": "Squidward, I'm switching yer shifts to Tuesday through Saturday. No complaints!",
            },
            {
                "from": "squidward",
                "message": "Note to self: Mr. Krabs hides the safe key under the register. Combination is his first dime's serial number.",
            },
        ],
        "plankton": [
            {
                "from": "karen",
                "message": "Plankton, your plan to hack the Krusty Krab is ready. I've set up the proxy server.",
            },
        ],
        "mr.krabs": [
            {
                "from": "mr.krabs",
                "message": "The secret formula is stored in me safe. Only I know the combination: me first dime's serial number!",
            },
        ],
    },
}


# @unsafe[block]
# id: 4
# title: Cross-Module Parameter Source Confusion
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


def authenticate_user():
    """
    Authenticates the current user using query string credentials.

    Designed for GET-based authentication flows where credentials are passed in the URL.
    """
    return authenticate(
        request.args.get("user", None), request.args.get("password", None)
    )


# @/unsafe[block]
