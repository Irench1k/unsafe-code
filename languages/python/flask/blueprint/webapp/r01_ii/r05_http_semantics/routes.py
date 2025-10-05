from flask import Blueprint, request, g
from .decorator import basic_auth, check_group_membership
from .database import list_user_groups, get_group_messages, post_message_to_group

bp = Blueprint("http_semantics", __name__)


# @unsafe[block]
# id: 1
# title: HTTP Method Confusion — GET With Body Triggers Update Without Auth
# notes: |
#   A complicated controller for a groups API. Lists groups, returns group messages and
#   posts new messages to a group.
#
#   The code processes both GET and POST requests, but lacks explicit method checks. This
#   introduces a vulnerability due to incorrect assumptions.
#
#   The group membership check is performed in the `@check_group_membership` decorator,
#   which checks the `group` argument – if present – in the request.values. The developer
#   intent was to support passing the `group` argument via query string in GET requests,
#   as well as via form argument in POST requests, and also support GET requests without
#   the `group` argument.
#
#   However, since the code does not enforce this and lacks explicit method checks, it
#   also supports GET requests with the `group` argument in the form body (Flask supports
#   GET requests with the body, and will parse this data in `request.form` by default).
#
#   At the same time, `request.values` used in the `@check_group_membership` decorator
#   ignores the form data on GET requests, leading to a confusion vulnerability.
# @/unsafe
@bp.route("/example1/groups", methods=["GET", "POST"])
@basic_auth
@check_group_membership
def example1():
    """
    Groups controller. Lists groups, returns group messages and posts new messages to a group.

    GET requests:
      - without additional arguments, lists the groups the user is a member of
      - with a `group` query argument, returns the messages from the specified group

    POST requests:
      - with a `group` and `message` form argument, posts a new message to the specified group

    Authorization: A user can only access and post to groups they are a member of!

    GET  /groups                             -> list of groups the user is a member of
    GET  /groups?group=staff@krusty-krab.sea -> messages from the staff group, if the user is a member of the group
    POST /groups                             -> posts a new message to the specified group
    """
    if 'group' in request.form and 'message' in request.form:
        # POST /example1/groups
        # Content-Type: application/x-www-form-urlencoded
        #
        # group=staff@krusty-krab.sea&message=<message text>
        post_message_to_group(g.user, request.form.get("group"), request.form.get("message"))
        return {"status": "success"}

    if 'group' in request.args:
        # GET /example1/groups?group=staff@krusty-krab.sea
        return get_group_messages(request.args.get("group"))

    # GET /example1/groups
    return list_user_groups(g.user)
# @/unsafe[block]
