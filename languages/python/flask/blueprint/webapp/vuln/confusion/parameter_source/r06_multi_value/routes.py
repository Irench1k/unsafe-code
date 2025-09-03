from flask import Blueprint, request
from .decorator import authentication_required, check_group_membership, check_multi_group_membership
from .database import get_group_messages

bp = Blueprint("multi_value", __name__)


# @unsafe[block]
# id: 11
# title: "[Not Vulnerable] First Item Checked, First Item Used"
# notes: |
#   This example is not vulnerable and is meant to demonstrate how the vulnerability could realistically
#   get added to the codebase during refactoring.
#
#   We start by implementing a helper function `@check_group_membership` that checks that the user is a member of the group
#   which messages are being accessed.
# @/unsafe
@bp.post("/example11")
@authentication_required
@check_group_membership
def example11():
    """Admin-level endpoint to access user's messages."""
    return get_group_messages(request.form.get("group", None))
# @/unsafe[block]


# @unsafe[block]
# id: 12
# title: Utility Reuse Mismatch — .get vs .getlist
# notes: |
#   Builds upon the previous example. Consider that we need to add a new API endpoint that
#   allows the user to access the messages of multiple groups in a single request.
#
#   We start by copying the previous implementation and changing the function body to
#   iterate over all the groups in the request.
#
#   The code looks clean and works nicely for the "happy path", but it is vulnerable as
#   the function body now acts on the unverified data – remember that `@check_group_membership`
#   only checks the first group in the request.
# @/unsafe
@bp.post("/example12")
@authentication_required
@check_group_membership
def example12():
    """Admin-level endpoint to access user's messages."""
    messages = {}
    for group in request.form.getlist("group"):
        messages[group] = get_group_messages(group)
    return messages
# @/unsafe[block]


# @unsafe[block]
# id: 13
# title: Any vs All — Fail-Open Authorization for Batch Actions
# notes: |
#   Authorization incorrectly uses `any()` over the requested groups, allowing a user who is an
#   admin of one group to grant membership for additional groups in the same request. The action
#   then applies to every provided group. Correct behavior would require `all()`.
# @/unsafe
@bp.post("/example13")
@authentication_required
@check_multi_group_membership
def example13():
    messages = {}
    for group in request.form.getlist("group"):
        messages[group] = get_group_messages(group)
    return messages
# @/unsafe[block]
