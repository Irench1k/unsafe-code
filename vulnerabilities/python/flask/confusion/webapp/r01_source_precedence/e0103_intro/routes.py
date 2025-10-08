from flask import Blueprint, request

bp = Blueprint("source_precedence_intro", __name__)

db = {
    "passwords": {"spongebob": "bikinibottom", "squidward": "clarinet123"},
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
    },
}


# @unsafe[function]
# id: 1
# title: Secure Implementation
# http: open
# notes: |
#   Here you can see a secure implementation that consistently uses query string parameters
#   for both authentication and data retrieval.
# @/unsafe
@bp.route("/example1", methods=["GET", "POST"])
def example1():
    """
    Retrieves messages for an authenticated user.

    Uses query string parameters for both authentication and message retrieval,
    ensuring consistent parameter sourcing throughout the request lifecycle.
    """
    user = request.args.get("user", None)

    password = db["passwords"].get(user, None)
    if password is None or password != request.args.get("password", None):
        return "Invalid user or password", 401

    messages = db["messages"].get(user, None)
    if messages is None:
        return "No messages found", 404

    return messages


# @unsafe[function]
# id: 2
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
#   Here you can see if we provide squidward's name in the request body, we can access his messages without his password.
# @/unsafe
@bp.route("/example2", methods=["GET", "POST"])
def example2():
    """
    Retrieves messages for an authenticated user.

    Supports flexible parameter passing to accommodate various client implementations.
    """
    user = request.args.get("user", None)

    password = db["passwords"].get(user, None)
    if password is None or password != request.args.get("password", None):
        return "Invalid user or password", 401

    # Allow form data to specify the target user for message retrieval
    user = request.form.get("user", None)
    messages = db["messages"].get(user, None)
    if messages is None:
        return "No messages found", 404

    return messages


# @unsafe[block]
# id: 3
# title: Function-Level Parameter Source Confusion
# http: open
# notes: |
#   Functionally equivalent to example 2, but shows how separating authentication and data retrieval into different functions can make the vulnerability harder to spot.
# @/unsafe
def authenticate(user, password):
    """Validates user credentials against the database."""
    if password is None or password != db["passwords"].get(user, None):
        return False
    return True


def get_messages(user):
    """Retrieves all messages for the specified user."""
    messages = db["messages"].get(user, None)
    if messages is None:
        return None
    return {"owner": user, "messages": messages}


@bp.route("/example3", methods=["GET", "POST"])
def example3():
    """
    Retrieves messages for an authenticated user.

    Uses modular authentication and data retrieval functions for cleaner separation of concerns.
    """
    if not authenticate(
        request.args.get("user", None), request.args.get("password", None)
    ):
        return "Invalid user or password", 401

    messages = get_messages(request.form.get("user", None))
    if messages is None:
        return "No messages found", 404

    return messages


# @/unsafe[block]
