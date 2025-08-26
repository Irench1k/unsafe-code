from flask import Blueprint, request

bp = Blueprint("request_values", __name__)


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


# @unsafe[block]
# id: 6
# title: Form Authentication Bypass
# request-details: open
# notes: |
#   The endpoint uses form data for authentication, but request.values.get() allows query
#   parameters to override form values, creating a vulnerability. Although designed for POST
#   requests, the endpoint accepts both GET and POST methods, enabling the attack.
#
#   Note that although the regular usage would rely on POST request (or PUT, PATCH, etc.),
#   and wouldn't work with GET (because flask's request.values ignores form data in GET
#   requests), the attacker can send both GET and POST requests (if the endpoint is
#   configured to accept both methods).
#
#  ```http
#  POST /vuln/confusion/parameter-source/example6? HTTP/1.1
#  Content-Type: application/x-www-form-urlencoded
#  Content-Length: 26
#
#  user=alice&password=123456
#  ```
#
#  However, the attacker can send both GET and POST requests (if the endpoint is configured to accept both methods).
# @/unsafe
def authenticate_user_example6():
    """Authenticate the user, based solely on the request body."""
    return authenticate(
        request.form.get("user", None), request.form.get("password", None)
    )


@bp.route("/example6", methods=["GET", "POST"])
def example6():
    if not authenticate_user_example6():
        return "Invalid user or password", 401

    # The vulnerability occurs because flask's request.values merges the form and query string
    messages = get_messages(request.values.get("user", None))
    if messages is None:
        return "No messages found", 404

    return messages


# @/unsafe[block]


# @unsafe[block]
# id: 7
# title: Request.Values in Authentication
# notes: |
#   Demonstrates how using request.values in authentication while using form data for access creates vulnerabilities.
#
#   This is an example of a varient of example 6, as we do the similar thing, but now we can pass Bob's username in the request body with Alice's password, while passing Alice's username in the request query.
#   Note that this example does not work with GET request, use POST.
# @/unsafe
def authenticate_user_example7():
    """Authenticate the user, based solely on the request body."""
    return authenticate(
        request.values.get("user", None), request.values.get("password", None)
    )


@bp.route("/example7", methods=["GET", "POST"])
def example7():
    if not authenticate_user_example7():
        return "Invalid user or password", 401

    messages = get_messages(request.form.get("user", None))
    if messages is None:
        return "No messages found", 404

    return messages


# @/unsafe[block]
