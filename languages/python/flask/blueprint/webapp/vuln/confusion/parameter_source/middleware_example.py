from flask import Blueprint, request

# @unsafe[file]
# id: flask-vuln-confusion-parametersource-009
# title:
# category:
# complexity:
# files:
# notes:
# @/unsafe

bp = Blueprint("middleware", __name__)

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


def get_user():
    user_from_form = request.form.get("user", None)
    user_from_args = request.args.get("user", None)

    return user_from_form or user_from_args


def get_messages(user):
    messages = db["messages"].get(user, None)
    if messages is None:
        return None
    return {"owner": user, "messages": messages}


@bp.before_request
def verify_user():
    """Authenticate the user, based solely on the request query string."""
    if not authenticate(
        request.args.get("user", None), request.args.get("password", None)
    ):
        return "Invalid user or password", 401

    # In Flask, if the middleware returns non-None value, the value is handled as if it was
    # the return value from the view, and further request handling is stopped
    return None


# The expected usage:
#   GET /vuln/confusion/parameter-source/example9?user=alice&password=123456 HTTP/1.0
#
# Attack:
#   GET /vuln/confusion/parameter-source/example9?user=alice&password=123456 HTTP/1.0
#   Content-Type: application/x-www-form-urlencoded
#   Content-Length: 10
#
#   user=bob


@bp.route("/example9", methods=["GET", "POST"])
def example9():
    messages = get_messages(get_user())
    if messages is None:
        return "No messages found", 404
    return messages
