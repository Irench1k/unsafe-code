from flask import Blueprint, g, request

from .database import get_group_messages, post_message_to_group
from .decorator import basic_auth, check_group_membership

bp = Blueprint("authz_simple_rebinding", __name__)


# @unsafe[block]
# id: 16
# title: "Classic Authorization Binding Drift - User Identity Rebinding"
# notes: |
#   This demonstrates the most straightforward form of authorization binding drift:
#   the application authenticates WHO the user is, verifies they have access to a
#   resource, but then trusts a user-controlled parameter to determine which
#   identity to ACT AS.
#
#   THE VULNERABILITY: Identity rebinding after successful authorization.
#   - Authentication establishes WHO: Squidward (verified via Basic Auth) ✓
#   - Authorization checks WHICH resource: staff@krusty-krab.sea (verified member) ✓
#   - Action uses DIFFERENT identity: spongebob@krusty-krab.sea (from request body) ✗
#
#   This is the purest form of authorization binding drift: we authenticate the
#   user correctly, we authorize them for the correct resource, but then we let
#   them rebind their identity when performing the action.
#
#   Key insight: This is NOT about confused parameters or different sources.
#   It's about trusting user input for identity AFTER authentication succeeded.
#
#   Attack scenario:
#   1. Mr. Krabs announces Employee of the Month voting in the staff group
#   2. Squidward (who desperately wants the recognition) authenticates as himself
#   3. He's authorized to post to staff@krusty-krab.sea (he's a member)
#   4. But the API trusts the "from_user" parameter from the request body
#   5. Squidward posts a vote for himself while claiming it's from SpongeBob
#
#   Impact: Squidward can impersonate SpongeBob and manipulate the vote!
# @/unsafe
@bp.post("/example16/groups/<group>/messages")
@basic_auth
@check_group_membership
def example16_post_message(group):
    """
    Posts a message to a group.

    Request body: { "from_user": "email", "message": "text" }

    The from_user field allows attribution flexibility for cases like:
    - Delegated posting (assistants posting on behalf of managers)
    - System notifications sent on behalf of administrators
    - Message forwarding from external systems

    Strict authentication via Basic Auth ensures only authorized users
    can post to groups they're members of.
    """
    data = request.get_json()
    if not data:
        return {"error": "Request body required"}, 400

    from_user = data.get("from_user")
    message = data.get("message")

    if not from_user or not message:
        return {"error": "Missing required fields: from_user, message"}, 400

    # Authenticated users can only post to groups they're members of (checked by decorator)
    post_message_to_group(from_user, group, message)
    return {"status": "success", "from": from_user, "to_group": group}


@bp.get("/example16/groups/<group>/messages")
@basic_auth
@check_group_membership
def example16_get_messages(group):
    """Retrieves all messages from a group."""
    return get_group_messages(group)
# @/unsafe[block]
