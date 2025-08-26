from flask import request

db = {
    "passwords": {"alice": "123456", "bob": "mypassword"},
    "messages": {
        "alice": [
            {"from": "kevin", "message": "Hi Alice, you're fired!"},
        ],
        "bob": [
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


def get_messages(user):
    messages = db["messages"].get(user, None)
    if messages is None:
        return None
    return {"owner": user, "messages": messages}


def authenticate():
    """Authenticate the user, based solely on the request query string."""
    user = request.args.get("user", None)
    password = request.args.get("password", None)

    if password is None or password != db["passwords"].get(user, None):
        return False
    return True


def get_user():
    user_from_form = request.form.get("user", None)
    user_from_args = request.args.get("user", None)

    return user_from_form or user_from_args
