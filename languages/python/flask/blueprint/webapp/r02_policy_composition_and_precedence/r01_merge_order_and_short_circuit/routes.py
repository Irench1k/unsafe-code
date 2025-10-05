from flask import Blueprint, g
from .decorator import basic_auth_v3, check_group_membership_v2
from .database import get_group_messages

bp = Blueprint("merge_order_and_short_circuit", __name__)

# @unsafe[block]
# id: 1
# title: "Authorization Bypass via Decorator Execution Order"
# notes: |
#   We try to fix the root cause of the vulnerability here by enforcing correct
#   merging order – view args take precedence over query args. Additionally, we
#   enforce that only one of the two can be present.
#
#   The code, however, remains vulnerable despite these efforts! This time, the
#   problem is that the `@check_group_membership_v2` decorator is applied too
#   early – before the `@basic_auth_v3` decorator which is responsible for setting
#   the `g.group` global variable. This makes `@check_group_membership_v2` a no-op.
#
#   This is a pure policy composition issue: the guard decorator executes before
#   the authentication decorator prepares the state it depends on. Flask applies
#   decorators bottom-up (outer decorator runs first), so @check_group_membership_v2
#   sees g.group = None and passes all requests.
# @/unsafe
@bp.get("/example1/groups/<group>/messages")
@check_group_membership_v2
@basic_auth_v3
def example1_group_messages(group):
    """Returns group's messages, if the user is a member of the group."""
    return get_group_messages(group)
# @/unsafe[block]
