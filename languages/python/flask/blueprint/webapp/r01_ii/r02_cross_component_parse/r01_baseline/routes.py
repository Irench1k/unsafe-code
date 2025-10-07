from flask import Blueprint, request
from .decorator import authentication_required
from .database import get_messages, authenticate

bp = Blueprint("baseline", __name__)

# @unsafe[block]
# id: 1
# title: "Consistent Parameter Sourcing [Not Vulnerable]"
# notes: |
#   This baseline demonstrates the secure pattern for handling authentication
#   when decorators and handlers need to access the same user identity.
#
#   THE SECURE PATTERN: Consistent parameter sourcing across all layers.
#   - Authentication decorator validates credentials from request.args
#   - Handler retrieves user identity from the SAME source (request.args)
#   - Both layers use identical logic: request.args.get("user")
#   - Result: Authentication and data access work on the same identity
#
#   This prevents authentication bypass by ensuring that the identity
#   validated during authentication is the exact same identity used for
#   data access. There is no confusion between different request data sources.
#
#   Compare this to the vulnerable examples that follow, where different
#   layers source the user identity from different request properties,
#   creating authentication bypass vulnerabilities.
# @/unsafe
@bp.route("/example1", methods=["GET", "POST"])
@authentication_required
def example1():
    """
    Returns user's messages after authentication.

    Securely retrieves user identity from the same source used for
    authentication (query parameters), preventing any confusion.
    """
    user = request.args.get("user")
    messages = get_messages(user)
    if messages is None:
        return "No messages found", 404
    return messages
# @/unsafe[block]
