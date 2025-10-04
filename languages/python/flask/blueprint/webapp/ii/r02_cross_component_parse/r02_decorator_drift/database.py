from flask import request

# Simulated database - simple authentication bypass examples
db = {
    "users": {
        "alice": {
            "password": "123456",
            "messages": [
                {"from": "kevin", "message": "Hi Alice, you're fired!"},
            ],
        },
        "bob": {
            "password": "mypassword",
            "messages": [
                {
                    "from": "kevin",
                    "message": "Hi Bob, here is the password you asked for: P@ssw0rd!",
                },
                {
                    "from": "michael",
                    "message": "Hi Bob, come to my party on Friday! The secret passphrase is 'no-one-knows-it'!",
                },
            ],
        },
    }
}


# Example 8 helpers
def get_messages_ex8(user):
    """Retrieve messages for a user."""
    messages = db["users"].get(user, {}).get("messages", None)
    if messages is None:
        return None
    return {"owner": user, "messages": messages}


def authenticate_ex8():
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


def get_user_ex8():
    """
    Get the user identity from request data.

    VULNERABILITY: Prioritizes form data over query parameters, creating
    a source precedence confusion with authenticate_ex8().
    """
    user_from_form = request.form.get("user", None)
    user_from_args = request.args.get("user", None)

    return user_from_form or user_from_args
