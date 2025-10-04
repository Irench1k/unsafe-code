from flask import Blueprint
from .decorator import authentication_required
from .database import get_messages_ex8, get_user_ex8

bp = Blueprint("decorator_drift", __name__)

# @unsafe[block]
# id: 8
# title: "Decorator-based Authentication with Parsing Drift"
# notes: |
#   Shows how using decorators can obscure parameter source confusion, leading
#   to authentication bypass.
#
#   Example 8 is functionally equivalent to Example 4 from the source precedence
#   examples, but it may be harder to spot the vulnerability when using decorators
#   because the parameter source logic is split across multiple layers.
#
#   THE VULNERABILITY: Authentication bypass via source precedence confusion.
#   - Authentication decorator validates credentials from request.args (query string)
#   - Handler retrieves user identity from get_user_ex8(), which prioritizes request.form
#   - Attack: Provide Alice's credentials in query string, Bob's name in form body
#   - Result: Authenticate as Alice, but access Bob's messages
#
#   This is NOT authorization binding drift - it's authentication bypass because
#   the authenticated identity itself gets confused between authentication check
#   and data access.
# @/unsafe
@bp.route("/example8", methods=["GET", "POST"])
@authentication_required
def example8():
    messages = get_messages_ex8(get_user_ex8())
    if messages is None:
        return "No messages found", 404
    return messages
# @/unsafe[block]
