from flask import Blueprint, request
from .database import get_messages, get_user
from .middleware import register_middleware

bp = Blueprint("middleware_drift", __name__)
register_middleware(bp)


# @unsafe[block]
# id: 9
# title: "Middleware-based Authentication with Parsing Drift"
# notes: |
#   Demonstrates how Flask's middleware system can contribute to parameter source confusion.
#
#   Example 9 is functionally equivalent to Example 4 from the old parameter source
#   confusion examples, but it may be harder to spot the vulnerability while using middleware.
#
#   The before_request middleware authenticates using request.args.get("user"), but the
#   handler retrieves the user via get_user(request) which prioritizes request.form over
#   request.args. This allows an attacker to authenticate as Alice but access Bob's messages.
# @/unsafe
@bp.route("/example9", methods=["GET", "POST"])
def example9():
    messages = get_messages(get_user(request))
    if messages is None:
        return "No messages found", 404
    return messages


# @/unsafe[block]
