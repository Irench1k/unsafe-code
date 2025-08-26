from flask import Blueprint, request
from functools import wraps

bp = Blueprint("decorator", __name__)


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


def authenticate(user, password):
    if password is None or password != db["passwords"].get(user, None):
        return False
    return True


def get_messages(user):
    messages = db["messages"].get(user, None)
    if messages is None:
        return None
    return {"owner": user, "messages": messages}


def authenticate_user():
    """Authenticate the user, based solely on the request query string."""
    return authenticate(
        request.args.get("user", None), request.args.get("password", None)
    )


def get_user():
    user_from_form = request.form.get("user", None)
    user_from_args = request.args.get("user", None)

    return user_from_form or user_from_args


# @unsafe[block]
# id: 8
# title: Decorator-based Authentication
# notes: |
#   Shows how using decorators can obscure parameter source confusion.
#
#   Example 8 is functionally equivalent to Example 4, but it may be harder to spot the vulnerability while using decorators.
# @/unsafe
def authentication_required(f):
    @wraps(f)
    def decorated_example8(*args, **kwargs):
        if not authenticate_user():
            return "Invalid user or password", 401
        return f(*args, **kwargs)

    return decorated_example8


@bp.route("/example8", methods=["GET", "POST"])
@authentication_required
def example8():
    messages = get_messages(get_user())
    if messages is None:
        return "No messages found", 404
    return messages


# @/unsafe[block]
