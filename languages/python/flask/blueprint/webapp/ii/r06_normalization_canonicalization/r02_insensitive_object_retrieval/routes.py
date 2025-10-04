from flask import Blueprint, request
from .decorator import basic_auth, check_group_membership
from .database import get_group_messages, add_group

bp = Blueprint("lowercase2", __name__)

# @unsafe[block]
# id: 19
# title: Case insensitive Object Retrieval
# notes: |
#   In this example we are still using case canonicalization for group retrieval, 
#   but now instead of showing the attacker the victim's group content, 
#   we are showing the attacker's newly created group content to the victim, allowing impersonation.
#
#   The vulnerability occurs when an attacker creates a new group with the same name as the victim's group 
#   but uses different casing.During group creation, the system checks for exact name matches to enforce uniqueness, 
#   so "STAFF@KRUSTY-KRAB.SEA" is considered different from "staff@krusty-krab.sea" and creation succeeds. 
#   However, during group retrieval, the system performs case-insensitive matching and returns the most recently 
#   created group that matches. When the victim tries to access their original group "staff@krusty-krab.sea", 
#   they actually receive the attacker's group "STAFF@KRUSTY-KRAB.SEA" because it was added later 
#   and the case-insensitive lookup treats them as the same group.
#
#   This vulnerability allows the attacker to impersonate legitimate group members and post messages 
#   that appear to come from trusted colleagues or administrators, potentially leading to social engineering 
#   attacks and information disclosure.
# @/unsafe
@bp.get("/example19/groups/<group>/messages")
@basic_auth
@check_group_membership
def example19(group):
    return get_group_messages(group)


@bp.post("/example19/groups")
@basic_auth
def example19_post():
    name = request.json["name"]
    users = request.json["users"]
    messages = request.json["messages"]
    add_group(name, users, messages)
    return {"status": "ok"}
# @/unsafe[block]
