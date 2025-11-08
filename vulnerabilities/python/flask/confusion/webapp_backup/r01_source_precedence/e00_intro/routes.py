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
# notes: |
#   Here you can see a secure implementation that consistently uses form body parameters
#   for both authentication and data retrieval.
# @/unsafe
@bp.post("/example1")
def example1():
    """Retrieves messages for an authenticated user."""
    user = request.form.get("user")
    if not user:
        return "Invalid user or password", 401

    password = db["passwords"].get(user)
    if not password or password != request.form.get("password"):
        return "Invalid user or password", 401

    messages = db["messages"].get(user, [])

    return messages


# @unsafe[function]
# id: 2
# title: Inline request.form vs request.args Confusion
# notes: |
#   Demonstrates the most basic form of parameter source confusion where authentication
#   uses **form body** parameters but data retrieval uses **query string** parameters.
#
#   An attacker authenticates with their own credentials in the body while specifying
#   a victim's username in the URL.
# @/unsafe
@bp.post("/example2")
def example2():
    """Retrieves messages for an authenticated user."""
    # Verify that user is authenticated
    password = db["passwords"].get(request.form.get("user"))
    if not password or password != request.form.get("password"):
        return "Invalid user or password", 401

    # Retrieve messages for the authenticated user
    messages = db["messages"].get(request.args.get("user"), [])

    return messages


# @unsafe[block]
# id: 3
# title: Function-Level Parameter Source Confusion
# notes: |
#   Separating authentication and data retrieval into different functions can make the
#   vulnerability harder to spot.
# @/unsafe
@bp.post("/example3")
def example3():
    """
    Retrieves messages for an authenticated user.

    Uses modular authentication and data retrieval functions for cleaner separation of concerns.
    """
    principal = resolve_principal(request)
    if not authenticate(principal, request.form.get("password")):
        return "Invalid user or password", 401
    return messages_get(request)


def messages_get(request):
    """Retrieves all messages for the specified user."""
    messages = db["messages"].get(request.form.get("user"), [])
    return messages


def authenticate(principal, password):
    """Validates user credentials against the database."""
    return password and password == db["passwords"].get(principal)


def resolve_principal(request):
    """Resolves the principal from the request."""
    return request.args.get("user")
# @/unsafe[block]
