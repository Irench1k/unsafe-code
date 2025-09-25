from flask import Blueprint, request
from .database import get_messages, get_user
from .middleware import register_middleware

bp = Blueprint("middleware", __name__)
register_middleware(bp)


# @unsafe[block]
# id: 9
# part: 1
# title: Middleware-based Authentication
# notes: |
#   Demonstrates how Flask's middleware system can contribute to parameter source confusion.
#
#   Example 9 is functionally equivalent to Example 4, but it may be harder to spot the vulnerability while using middleware.
# @/unsafe
@bp.route("/example9", methods=["GET", "POST"])
def example9():
    messages = get_messages(get_user(request))
    if messages is None:
        return "No messages found", 404
    return messages


# @/unsafe[block]
