from flask import Blueprint, request
from .r01_simplified_patterns.routes import bp as simplified_patterns_bp
from .r02_custom_helpers.routes import bp as custom_helpers_bp
from .r03_request_values.routes import bp as request_values_bp
from .r04_decorator.routes import bp as decorator_bp
from .r05_middleware.routes import bp as middleware_bp

# Confusion-based vulnerability examples
bp = Blueprint("parameter_source", __name__)

bp.register_blueprint(simplified_patterns_bp)
bp.register_blueprint(custom_helpers_bp)
bp.register_blueprint(request_values_bp)
bp.register_blueprint(decorator_bp)
bp.register_blueprint(middleware_bp)


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


# @unsafe[function]
# id: 0
# title: Secure Implementation
# image: image-0.png
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


# 1.3.x first item checked, all items used (build upon correct example with single item)
# - an endpoint to grant a user access to multiple groups: ?user=bob&grant_group=group1&grant_group=group2. The authentication check might only verify grant_group=group1, but the logic iterates through request.args.getlist('grant_group') and adds the user to both, potentially granting unauthorized access to group2
# - an example where the utility function was used for the handler that accessed .get("grant_group"), but another handler got added that accessed .getlist("grant_group") – reusing the same utility incorrectly
# 1.3.x any passing check vs all passing check (fail open / fail close)
# 1.3.x indirect access, passing to another function as json, etc
# 1.5.x path parameter overriden by query parameter
# - @bp.route("/users/<username>/messages")
# - a decorator authenticates the request: @permission_required(user=username) – via path only
# - the view uses g.user, set by the middleware, which is a merged dict
# - /users/alice/messages?username=bob
# - another pattern: reuse utility function that merges path and query params (meant for something else initially)
# - request.view_args: path parameters
# 1.5.x json vs others?
# - upsert some unexpected data due to partial validation (e.g. only check certain field, but pass the whole object)
# - a utility function that abstracts multipart and json body access
# - get a list or dict where a single value was expected
# 1.5.x manual query parsing before and after urldecode / unquote
# 1.5.x errors during normalization (e.g. lowercase, strip, unicode)
# 1.7 HTTP Method Confusion
# - view is registered with methods=["GET", "POST"]
# - POST is meant to update the resource, but different code paths don't explicitly check method
# - instead, the assumption is that the only POST can contain form data
# - flask lets access form data in GET as well when accessed via req.form, but not through req.values
# - a weak check only validates data from req.values and fails open on GET with form data
# 1.8 req.values seems to work with multipart/form-data in addition to application/x-www-form-urlencoded
# 1.9 g.user set from cookie / jwt
