from flask import Blueprint, request

bp = Blueprint("source_precedence", __name__)

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


@bp.route("/")
def index():
    return "Source Precedence vulnerability examples\n"


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


# @unsafe[block]
# id: 4
# title: Cross-Module Parameter Source Confusion
# notes: |
#   In the previous example, you can still see that the `user` value gets retrieved from the
#   `request.args` during validation but from the `request.form` during data retrieval.
#
#   A more subtle example, where this is not immediately obvious (imagine, `authenticate_user`
#   is defined in an another file altogether):
# @/unsafe
def authenticate_user():
    """
    Authenticates the current user using query string credentials.

    Designed for GET-based authentication flows where credentials are passed in the URL.
    """
    return authenticate(
        request.args.get("user", None), request.args.get("password", None)
    )


@bp.route("/example4", methods=["GET", "POST"])
def example4():
    """
    Retrieves messages for an authenticated user.

    Delegates authentication to a shared utility function while handling
    message retrieval directly in the endpoint.
    """
    if not authenticate_user():
        return "Invalid user or password", 401

    messages = get_messages(request.form.get("user", None))
    if messages is None:
        return "No messages found", 404

    return messages


# @/unsafe[block]


# @unsafe[block]
# id: 5
# title: Form-Query Priority Resolution
# notes: |
#   Shows how a helper function that implements source prioritization can create vulnerabilities.
#
#   In Example 5 we don't need to specify body parameters to get a result (which is now more realistic!), but if we want, we can still access squidward's messages by passing his user name in the request body:
# @/unsafe
def get_user():
    """
    Retrieves the user identifier from the request.

    Checks form data first for POST requests, falling back to query parameters
    to support both form submissions and direct URL access.
    """
    user_from_form = request.form.get("user", None)
    user_from_args = request.args.get("user", None)

    return user_from_form or user_from_args


@bp.route("/example5", methods=["GET", "POST"])
def example5():
    """
    Retrieves messages for an authenticated user.

    Uses a flexible user resolution strategy that accommodates multiple parameter sources.
    """
    if not authenticate_user():
        return "Invalid user or password", 401

    messages = get_messages(get_user())
    if messages is None:
        return "No messages found", 404
    return messages


# @/unsafe[block]


# @unsafe[block]
# id: 6
# title: Mixed-Source Authentication
# notes: |
#   Shows how authentication and data access can use different combinations of sources.
#
#   This one is interesting, because you can access Squidward's messages by providing his username and SpongeBob's password in the request query, while providing SpongeBob's username in the request body:
# @/unsafe
def authenticate_user_example6():
    """
    Authenticates the current user with flexible parameter resolution.

    Uses the user resolution helper for username while taking password from query string.
    """
    user = get_user()
    password = request.args.get("password", None)
    return authenticate(user, password)


@bp.route("/example6", methods=["GET", "POST"])
def example6():
    """
    Retrieves messages for an authenticated user.

    Combines flexible authentication with query-based message retrieval.
    """
    if not authenticate_user_example6():
        return "Invalid user or password", 401

    messages = get_messages(request.args.get("user", None))
    if messages is None:
        return "No messages found", 404
    return messages


# @/unsafe[block]


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


# @unsafe[function]
# id: 8
# title: Request.Values in Authentication
# notes: |
#   Demonstrates how using request.values in authentication while using form data for access creates vulnerabilities.
#
#   This is an example of a varient of example 7, as we do the similar thing, but now we can pass Squidward's username in the request body with SpongeBob's password, while passing SpongeBob's username in the request query. Note that this example does not work with GET request, use POST.
# @/unsafe
@bp.route("/example8", methods=["GET", "POST"])
def example8():
    """
    Retrieves messages for an authenticated user.

    Uses unified parameter resolution for authentication to support flexible client implementations,
    while retrieving messages based on form data.
    """
    # Authenticate using merged values from both query and form data
    if not authenticate(
        request.values.get("user", None), request.values.get("password", None)
    ):
        return "Invalid user or password", 401

    # Retrieve messages using form data
    messages = get_messages(request.form.get("user", None))
    if messages is None:
        return "No messages found", 404

    return messages
