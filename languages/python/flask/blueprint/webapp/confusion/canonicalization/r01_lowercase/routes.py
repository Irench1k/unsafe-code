from flask import Blueprint, request
from .decorator import basic_auth, check_group_membership
from .database import get_group_messages, add_group

bp = Blueprint("lowercase", __name__)

# @unsafe[block]
# id: 18
# title: Lowercase Normalization
# notes: |
#   This example demonstrates a canonicalization confusion vulnerability using inconsistent lowercase normalization.
#   
#   The vulnerability occurs because:
#
#   1. Users can create new groups with any casing (e.g., "STAFF@KRUSTY-KRAB.SEA"), making themselves admins
#
#   2. During group membership checks, the group name is NOT normalized/lowercased
#
#   3. When retrieving group messages, the group name IS normalized to lowercase
#   
#   Attack scenario:
#   Attacker creates a group "STAFF@KRUSTY-KRAB.SEA" (uppercase) and becomes admin.
#   When checking membership, system looks for "STAFF@KRUSTY-KRAB.SEA" (finds attacker's group).
#   When retrieving messages, system normalizes to "staff@krusty-krab.sea" (finds legitimate group).
#   As a result: Attacker gains access to messages from the legitimate group they shouldn't see.
# @/unsafe
@bp.get("/example18/groups/<group>/messages")
@basic_auth
@check_group_membership
def example18(group):
    return get_group_messages(group)


@bp.post("/example18/groups")
@basic_auth
def example18_post():
    name = request.json["name"]
    users = request.json["users"]
    add_group(name, users)
    return {"status": "ok"}
# @/unsafe[block]
