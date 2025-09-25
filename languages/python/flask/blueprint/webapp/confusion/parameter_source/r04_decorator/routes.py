from flask import Blueprint
from .database import get_messages, get_user
from .decorator import authentication_required


bp = Blueprint("decorator", __name__)


# @unsafe[block]
# id: 8
# part: 1
# title: Decorator-based Authentication
# notes: |
#   Shows how using decorators can obscure parameter source confusion.
#
#   Example 8 is functionally equivalent to Example 4, but it may be harder to spot the vulnerability while using decorators.
# @/unsafe
@bp.route("/example8", methods=["GET", "POST"])
@authentication_required
def example8():
    messages = get_messages(get_user())
    if messages is None:
        return "No messages found", 404
    return messages


# @/unsafe[block]
