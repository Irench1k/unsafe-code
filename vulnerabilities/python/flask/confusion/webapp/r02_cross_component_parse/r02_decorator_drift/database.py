from flask import request

# Simulated database - simple authentication bypass examples
db = {
    "users": {
        "spongebob": {
            "password": "bikinibottom",
            "messages": [
                {"from": "patrick", "message": "Hey SpongeBob, wanna go jellyfishing?"},
            ],
        },
        "squidward": {
            "password": "clarinet123",
            "messages": [
                {
                    "from": "plankton",
                    "message": "Squidward, I'll pay you handsomely to 'accidentally' share the secret formula. You deserve better than that dead-end cashier job!",
                },
                {
                    "from": "mr.krabs",
                    "message": "Squidward, the new safe combination is 4-2-0-6-9. Don't write it down anywhere!",
                },
            ],
        },
    }
}


# Example 2 helpers
def get_messages_ex2(user):
    """Retrieve messages for a user."""
    messages = db["users"].get(user, {}).get("messages", None)
    if messages is None:
        return None
    return {"owner": user, "messages": messages}


def authenticate_ex2():
    """
    Authenticate the user based solely on the request query string.

    VULNERABILITY: Only checks credentials from request.args, but the handler
    may get the user identity from a different source.
    """
    user = request.args.get("user", None)
    password = request.args.get("password", None)

    if password is None or password != db["users"].get(user, {}).get("password", None):
        return False
    return True


def get_user_ex2():
    """
    Get the user identity from request data.

    VULNERABILITY: Prioritizes form data over query parameters, creating
    a source precedence confusion with authenticate_ex2().
    """
    user_from_form = request.form.get("user", None)
    user_from_args = request.args.get("user", None)

    return user_from_form or user_from_args
