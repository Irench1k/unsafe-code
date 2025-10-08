from flask import Blueprint, request

bp = Blueprint("source_precedence_apparent_fix", __name__)

# Database for examples 7-8
db = {
    "passwords": {
        "spongebob": "bikinibottom",
        "squidward": "clarinet123",
        "plankton": "chumbucket",
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


# Helper functions for examples 7-8
def authenticate(user, password):
    """Validates user credentials against the database."""
    return password is not None and password == db["passwords"].get(user, None)


def get_messages(user):
    """Retrieves all messages for the specified user."""
    messages = db["messages"].get(user, None)
    if messages is None:
        return None
    return {"owner": user, "messages": messages}


def reset_password(user, new_password):
    """Updates the user's password in the database."""
    if user not in db["passwords"]:
        return False
    db["passwords"][user] = new_password
    return True


# @unsafe[block]
# id: 7
# title: Form Authentication Bypass
# notes: |
#   The endpoint uses form data for authentication, but request.values.get() allows query parameters to override form values, creating a vulnerability. Although designed for POST requests, the endpoint accepts both GET and POST methods, enabling the attack.
#
#   Note that although the regular usage would rely on POST request (or PUT, PATCH, etc.), and wouldn't work with GET (because flask's request.values ignores form data in GET requests), the attacker can send both GET and POST requests (if the endpoint is configured to accept both methods).
#
#   ```http
#   POST /ii/source-precedence/example7? HTTP/1.1
#   Content-Type: application/x-www-form-urlencoded
#   Content-Length: 35
#
#   user=spongebob&password=bikinibottom
#   ```
#
#   However, the attacker can send both GET and POST requests (if the endpoint is configured to accept both methods).
# @/unsafe
def authenticate_user_example7():
    """
    Authenticates the user using form-based credentials.

    Designed for POST-based form submissions where credentials are in the request body.
    """
    return authenticate(
        request.form.get("user", None), request.form.get("password", None)
    )


@bp.route("/example7", methods=["GET", "POST"])
def example7():
    """
    Retrieves messages for an authenticated user.

    Uses form-based authentication with unified parameter resolution for message retrieval.
    """
    if not authenticate_user_example7():
        return "Invalid user or password", 401

    # Use request.values for flexible parameter resolution across query and form data
    messages = get_messages(request.values.get("user", None))
    if messages is None:
        return "No messages found", 404

    return messages


# @/unsafe[block]


# Note: This endpoint was FIXED by using request.values consistently for both authentication
# and message retrieval. This is the correct pattern - no parameter source confusion.
# However, see the password_reset endpoint below where the same developers made a mistake...
@bp.route("/example8", methods=["GET", "POST"])
def example8():
    """
    Retrieves messages for an authenticated user.

    Uses unified parameter resolution for both authentication and message retrieval,
    ensuring consistent parameter sourcing throughout the request lifecycle.
    """
    # Authenticate using merged values from both query and form data
    if not authenticate(
        request.values.get("user", None), request.values.get("password", None)
    ):
        return "Invalid user or password", 401

    # Retrieve messages using consistent request.values
    messages = get_messages(request.values.get("user", None))
    if messages is None:
        return "No messages found", 404

    return messages


# @unsafe[function]
# id: 8
# title: Password Reset Parameter Confusion
# notes: |
#   Developers "fixed" the messages endpoint but introduced a NEW vulnerability when adding
#   password reset functionality. Authentication uses request.values to verify WHO is making
#   the request, but the target user whose password gets reset comes from request.form only.
#
#   An attacker can authenticate with their own credentials in the query string while
#   specifying a victim's username in the form body, resetting the victim's password to
#   one they control. This enables full account takeover.
#
#   LESSON: This demonstrates how "apparent fixes" create false security. Same root cause
#   as Examples 2-7, but now enabling account takeover instead of just data disclosure.
#   The partial fix made developers careless when adding new features.
# @/unsafe
@bp.route("/example8/password_reset", methods=["POST"])
def example8_password_reset():
    """Resets a user's password after authentication."""
    # Authenticate using merged values (who's making the request)
    auth_user = request.values.get("user", None)
    auth_password = request.values.get("password", None)

    if not authenticate(auth_user, auth_password):
        return "Invalid user or password", 401

    # Target user and new password from form data (VULNERABILITY)
    target_user = request.form.get("user", None)
    new_password = request.form.get("new_password", None)

    if target_user is None or new_password is None:
        return "Missing required parameters", 400

    if reset_password(target_user, new_password):
        return {"status": "success", "user": target_user, "message": "Password updated"}
    else:
        return "User not found", 404
