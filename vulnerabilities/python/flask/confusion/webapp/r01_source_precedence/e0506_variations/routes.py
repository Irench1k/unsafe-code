from flask import Blueprint, request

bp = Blueprint("source_precedence_variations", __name__)

# Database for examples 5-6
db = {
    "passwords": {
        "spongebob": "bikinibottom",
        "squidward": "clarinet123",
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
        "mr.krabs": [
            {
                "from": "squidward",
                "message": "I saw Plankton buying a mechanical keyboard, he's planning to hack us!",
            },
        ],
    },
}


# Helper functions for examples 5-6
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


# @unsafe[block]
# id: 5
# title: Mixed-Source Authentication
# notes: |
#   Shows how authentication and data access can use different combinations of sources.
#
#   This one is interesting, because you can access Squidward's messages by providing his username and SpongeBob's password in the request query, while providing SpongeBob's username in the request body:
# @/unsafe
def get_user():
    """
    Retrieves the user identifier from the request.

    Checks form data first for POST requests, falling back to query parameters
    to support both form submissions and direct URL access.
    """
    user_from_form = request.form.get("user", None)
    user_from_args = request.args.get("user", None)

    return user_from_form or user_from_args


def authenticate_user_example5():
    """
    Authenticates the current user with flexible parameter resolution.

    Uses the user resolution helper for username while taking password from query string.
    """
    user = get_user()
    password = request.args.get("password", None)
    return authenticate(user, password)


@bp.route("/example5", methods=["GET", "POST"])
def example5():
    """
    Retrieves messages for an authenticated user.

    Combines flexible authentication with query-based message retrieval.
    """
    if not authenticate_user_example5():
        return "Invalid user or password", 401

    messages = get_messages(request.args.get("user", None))
    if messages is None:
        return "No messages found", 404
    return messages


# @/unsafe[block]


def delete_message(user, index):
    """Removes a message from the specified user's inbox."""
    messages = db["messages"].get(user, None)
    if messages is None or index < 0 or index >= len(messages):
        return False
    del messages[index]
    return True


# @unsafe[function]
# id: 6
# title: Destructive Parameter Source Confusion
# notes: |
#   Demonstrates parameter source confusion with a DELETE operation. Same root cause as
#   Examples 2-5, but now enabling destructive operations instead of just data disclosure.
#   Authentication uses query parameters while deletion target uses form body.
# @/unsafe
@bp.route("/example6", methods=["DELETE", "GET"])
def example6():
    """Manages user messages with list and delete operations."""
    if not authenticate_user():
        return "Invalid user or password", 401

    action = request.args.get("action", "delete")

    if action == "list":
        user = request.args.get("user")
        messages = get_messages(user)
        if messages is None:
            return "No messages found", 404
        return messages

    # Delete message - target user from form body (VULNERABILITY)
    target_user = request.form.get("user")
    message_index = int(request.args.get("index", 0))

    if delete_message(target_user, message_index):
        return {"status": "deleted", "user": target_user, "index": message_index}
    else:
        return "Message not found", 404


# Blueprint will be registered by parent routes.py
