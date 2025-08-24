from webbrowser import get
from flask import Blueprint, request
from functools import wraps

# Confusion-based vulnerability examples
bp = Blueprint("parameter_source", __name__)


@bp.route("/")
def index():
    return "Parameter source confusion vulnerability examples\n"


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

# 1. confusion between form and args:
# 1.1. the most obvious: req.form.get("a") vs req.args.get("a")


# No vulnerabilities here, we take the username and password from the query string arguments
# (not the best practice, but bear with me), and use the same values during the validation and
# data retrieval:
#
# GET /vuln/confusion/parameter-source/example1?user=alice&password=123456 HTTP/1.0
#
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


# A vulnerable example, we take the user name from the query string during the validation,
# but during the data retrieval another value is used, taken from the request body (form).
#
# GET /vuln/confusion/parameter-source/example1?user=alice&password=123456 HTTP/1.0
# Content-Length: 8
# Content-Type: application/x-www-form-urlencoded
#
# user=bob
#
# This does not look very realistic, but it demonstrates the core of the vulnerability,
# we will build upon this further.
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


# A more realistic example, functionally equivalent to example1, but is easier to overlook
# because the validation and data retrieval happen in different places.
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


# In the previous example, you can still see that the `user` value gets retrieved from the
# `request.args` during validation but from the `request.form` during data retrieval.
#
# A more subtle example, where this is not immediately obvious (imagine, `authenticat_user`
# is defined in an another file altogether):
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


# The example above is realistic and hard to detect, but there are still two issues with it:
# 1. the situation is unlikely to occur in exactly this way, because here
#    the request doesn't work at all if the `user` gets passed only via the query string
#    (it HAS to pass two `user` values, through query string and the body argument)
# 2. the second issue is that while calling verification function explicitly is valid,
#    a more common pattern is either using a decorator or a middleware.


# 1.2. req.form.get("a") vs req.values.get("a") [values merges args and form, with args having priority]


# Here we introduce a source confusion vulnerability, the `get_user` takes the value from
# the form if it exists, and falls back to the value from the query string.
def get_user():
    user_from_form = request.form.get("user", None)
    user_from_args = request.args.get("user", None)

    return user_from_form or user_from_args


# The regular requests (what developers expect) would look like this:
#   GET /vuln/confusion/parameter-source/example4?user=alice&password=123456 HTTP/1.0
# But an attacker can add another value for the `user`, placing it in the request body:
#   GET /vuln/confusion/parameter-source/example4?user=alice&password=123456 HTTP/1.0
#   Content-Type: application/x-www-form-urlencoded
#
#   user=bob
@bp.route("/example4", methods=["GET", "POST"])
def example4():
    if not authenticate_user():
        return "Invalid user or password", 401

    messages = get_messages(get_user())
    if messages is None:
        return "No messages found", 404
    return messages


# The opposite situation, where the `user` and `password` normally come from the request body:
#
#   POST /vuln/confusion/parameter-source/example5 HTTP/1.0
#   Content-Length: 26
#   Content-Type: application/x-www-form-urlencoded
#
#   user=alice&password=123456
#
# However, the `user` is also read from the query string. Note that although the regular
# usage would rely on POST request (or PUT, PATCH, etc.), and wouldn't work with GET
# (because flask's request.values ignores form data in GET requests), the attacker can
# send both GET and POST requests (if the endpoint is configured to accept both methods):
#
#  GET /vuln/confusion/parameter-source/example5?user=bob HTTP/1.0
#  Content-Length: 26
#  Content-Type: application/x-www-form-urlencoded
#
#  user=alice&password=123456
def authenticate_user_example5():
    """Authenticate the user, based solely on the request body."""
    return authenticate(
        request.form.get("user", None), request.form.get("password", None)
    )


@bp.route("/example5", methods=["GET", "POST"])
def example5():
    if not authenticate_user_example5():
        return "Invalid user or password", 401

    # The vulnerability occurs because flask's request.values merges the form and query string
    messages = get_messages(request.values.get("user", None))
    if messages is None:
        return "No messages found", 404

    return messages


# This is another way a vulnerability dynamically similar to example4 can occur in code:
#
# The regular usage would only rely on the query string:
#
# GET /vuln/confusion/parameter-source/example6?user=alice&password=123456 HTTP/1.0
#
# But an attacker can add the `user` value to the request body to change behavior. In this
# case, contrary to example4, the authentication will be performed based on the `user` value
# from the request body, while the messages will be retrieved based on the `user` value from
# the query string.
#
# GET /vuln/confusion/parameter-source/example6?user=bob&password=123456 HTTP/1.0
# Content-Type: application/x-www-form-urlencoded
# Content-Length: 8
#
# user=alice
def authenticate_user_example6():
    """Authenticate the user, based solely on the request query string."""
    user = get_user()
    password = request.args.get("password", None)
    return authenticate(user, password)


@bp.route("/example6", methods=["GET", "POST"])
def example6():
    if not authenticate_user_example6():
        return "Invalid user or password", 401

    messages = get_messages(request.args.get("user", None))
    if messages is None:
        return "No messages found", 404
    return messages


# Another example for a variant of example5, where the values are primarily read from the
# body, but attacker can change the behavior by adding extra `user` query string parameter.
#
# The expected usage:
#   POST /vuln/confusion/parameter-source/example7 HTTP/1.0
#   Content-Length: 26
#   Content-Type: application/x-www-form-urlencoded
#
#   user=alice&password=123456
#
# Attack:
#   POST /vuln/confusion/parameter-source/example7?user=alice HTTP/1.0
#   Content-Length: 24
#   Content-Type: application/x-www-form-urlencoded
#
#   user=bob&password=123456
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


# 1.2.3 req.values.get used as sanitizer in a decorator

# This is the same as example 4, but here we are using decorator instead of explicit call
#
# The expected usage:
#   GET /vuln/confusion/parameter-source/example8?user=alice&password=123456 HTTP/1.0
#
# Attack:
#   GET /vuln/confusion/parameter-source/example8?user=alice&password=123456 HTTP/1.0
#   Content-Type: application/x-www-form-urlencoded
#   Content-Length: 0
#
#   user=bob


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


# 1.2.4 req.values.get used as sanitizer in a middleware


# 1.3 wrong item checked
# 1.3.x first arg vs last
# 1.3.x first item checked, all items used (build upon correct example with single item)
# 1.3.x any passing check vs all passing check (fail open / fail close)
# 1.3.x indirect access, passing to another function as json, etc
# 1.4 multidict override
# 1.5 custom convenience functions for source merging
# 1.5.x path parameter overriden by query parameter
# 1.5.x json vs others?
# 1.5.x manual query parsing after urldecode
# 1.5.x errors during normalization (e.g. lowercase)
# 1.6 json type confusion
