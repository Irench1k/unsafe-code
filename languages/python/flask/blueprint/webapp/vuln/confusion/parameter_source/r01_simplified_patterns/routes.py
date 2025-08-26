from flask import Blueprint, request

bp = Blueprint("simplified_patterns", __name__)


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


# @unsafe[function]
# id: 1
# title: Basic Parameter Source Confusion
# notes: |
#   Demonstrates the most basic form of parameter source confusion where authentication
#   uses **query** parameters but data retrieval uses **form** data.
#
#   We take the user name from the query string during the validation,
#   but during the data retrieval another value is used, taken from the request body (form).
#   This does not look very realistic, but it demonstrates the core of the vulnerability,
#   we will build upon this further.
#
#   Here you can see if we provide bob's name in the request body, we can access his messages without his password.
# @/unsafe
@bp.route("/example1", methods=["GET", "POST"])
def example1():
    user = request.args.get("user", None)

    password = db["passwords"].get(user, None)
    if password is None or password != request.args.get("password", None):
        return "Invalid user or password", 401

    # Use the POST value which was not validated!
    user = request.form.get("user", None)
    messages = db["messages"].get(user, None)
    if messages is None:
        return "No messages found", 404

    return messages


# @unsafe[block]
# id: 2
# title: Function-Level Parameter Source Confusion
# request-details: open
# notes: |
#   Functionally equivalent to example 1, but shows how separating authentication and data retrieval into different functions can make the vulnerability harder to spot.
# @/unsafe
def authenticate(user, password):
    if password is None or password != db["passwords"].get(user, None):
        return False
    return True


def get_messages(user):
    messages = db["messages"].get(user, None)
    if messages is None:
        return None
    return {"owner": user, "messages": messages}


@bp.route("/example2", methods=["GET", "POST"])
def example2():
    if not authenticate(
        request.args.get("user", None), request.args.get("password", None)
    ):
        return "Invalid user or password", 401

    messages = get_messages(request.form.get("user", None))
    if messages is None:
        return "No messages found", 404

    return messages


# @/unsafe[block]


# @unsafe[block]
# id: 3
# title: Cross-Module Parameter Source Confusion
# notes: |
#   In the previous example, you can still see that the `user` value gets retrieved from the
#   `request.args` during validation but from the `request.form` during data retrieval.
#
#   A more subtle example, where this is not immediately obvious (imagine, `authenticat_user`
#   is defined in an another file altogether):
# @/unsafe
def authenticate_user():
    """Authenticate the user, based solely on the request query string."""
    return authenticate(
        request.args.get("user", None), request.args.get("password", None)
    )


@bp.route("/example3", methods=["GET", "POST"])
def example3():
    if not authenticate_user():
        return "Invalid user or password", 401

    messages = get_messages(request.form.get("user", None))
    if messages is None:
        return "No messages found", 404

    return messages


# @/unsafe[block]
