from flask import Blueprint, request

bp = Blueprint("source_precedence", __name__)

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


@bp.route("/")
def index():
    return "Source Precedence vulnerability examples\n"


# @unsafe[function]
# id: 0
# title: Secure Implementation
# http: open
# notes: |
#   Here you can see a secure implementation that consistently uses query string parameters
#   for both authentication and data retrieval.
# @/unsafe
@bp.route("/example0", methods=["GET", "POST"])
def example0():
    # Extract the user name from the query string arguments
    user = request.args.get("user", None)

    # Validate the user name
    password = db["passwords"].get(user, None)
    if password is None or password != request.args.get("password", None):
        return "Invalid user or password", 401

    # Retrieve the messages for the user
    messages = db["messages"].get(user, None)
    if messages is None:
        return "No messages found", 404

    # return the messages
    return messages


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
# http: open
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
#   A more subtle example, where this is not immediately obvious (imagine, `authenticate_user`
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


# @unsafe[block]
# id: 4
# title: Form-Query Priority Resolution
# notes: |
#   Shows how a helper function that implements source prioritization can create vulnerabilities.
#
#   In Example 4 we don't need to specify body parameters to get a result (which is now more realistic!), but if we want, we can still access bob's messages by passing his user name in the request body:
# @/unsafe
def get_user():
    user_from_form = request.form.get("user", None)
    user_from_args = request.args.get("user", None)

    return user_from_form or user_from_args


@bp.route("/example4", methods=["GET", "POST"])
def example4():
    if not authenticate_user():
        return "Invalid user or password", 401

    messages = get_messages(get_user())
    if messages is None:
        return "No messages found", 404
    return messages


# @/unsafe[block]


# @unsafe[block]
# id: 5
# title: Mixed-Source Authentication
# notes: |
#   Shows how authentication and data access can use different combinations of sources.
#
#   This one is interesting, because you can access Bob's messages by providing his username and Alice's password in the request query, while providing Alice's username in the request body:
# @/unsafe
def authenticate_user_example5():
    """Authenticate the user, based solely on the request query string."""
    user = get_user()
    password = request.args.get("password", None)
    return authenticate(user, password)


@bp.route("/example5", methods=["GET", "POST"])
def example5():
    if not authenticate_user_example5():
        return "Invalid user or password", 401

    messages = get_messages(request.args.get("user", None))
    if messages is None:
        return "No messages found", 404
    return messages


# @/unsafe[block]


# @unsafe[block]
# id: 6
# title: Form Authentication Bypass
# notes: |
#   The endpoint uses form data for authentication, but request.values.get() allows query parameters to override form values, creating a vulnerability. Although designed for POST requests, the endpoint accepts both GET and POST methods, enabling the attack.
#
#   Note that although the regular usage would rely on POST request (or PUT, PATCH, etc.), and wouldn't work with GET (because flask's request.values ignores form data in GET requests), the attacker can send both GET and POST requests (if the endpoint is configured to accept both methods).
#
#   ```http
#   POST /ii/source-precedence/example6? HTTP/1.1
#   Content-Type: application/x-www-form-urlencoded
#   Content-Length: 26
#
#   user=alice&password=123456
#   ```
#
#   However, the attacker can send both GET and POST requests (if the endpoint is configured to accept both methods).
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


# @unsafe[function]
# id: 7
# title: Request.Values in Authentication
# notes: |
#   Demonstrates how using request.values in authentication while using form data for access creates vulnerabilities.
#
#   This is an example of a varient of example 6, as we do the similar thing, but now we can pass Bob's username in the request body with Alice's password, while passing Alice's username in the request query. Note that this example does not work with GET request, use POST.
# @/unsafe
@bp.route("/example7", methods=["GET", "POST"])
def example7():
    # Authenticate using merged values
    if not authenticate(
        request.values.get("user", None), request.values.get("password", None)
    ):
        return "Invalid user or password", 401

    # But retrieve messages using only form data
    messages = get_messages(request.form.get("user", None))
    if messages is None:
        return "No messages found", 404

    return messages
