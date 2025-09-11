# Canonicalization Confusion Vulnerabilities in Flask
This directory contains examples demonstrating various patterns of canonicalization confusion vulnerabilities in Flask applications. These examples show how inconsistent canonicalization can lead to security vulnerabilities.
## Overview

Canonicalization is the process of transforming data into a "standard" form, for example, when you paste your email with the first upper case letter most of the email providers will convert it to the lower case, e.g. "Example@mail.com" -> "example@mail.com".

Canonicalization confusion occurs when an application uses the canonical form inconsistently, for example, it might be only used when accessing data but not during the security checks.

## Table of Contents

| Category | Example | File |
|:---:|:---:|:---:|
| Case Transformation | [Example 18: Lowercase Normalization](#ex-18) | [r01_lowercase/routes.py](r01_lowercase/routes.py#L27-L40) |
| Case Transformation | [Example 19: Case insensitive Object Retrieval](#ex-19) | [r02_insensitive_object_retrieval/routes.py](r02_insensitive_object_retrieval/routes.py#L27-L41) |

## Case Transformation
<a id="ex-18"></a>

### Example 18: Lowercase Normalization
This example demonstrates a canonicalization confusion vulnerability using inconsistent lowercase normalization.

The vulnerability occurs because:

1. Users can create new groups with any casing (e.g., "STAFF@KRUSTY-KRAB.SEA"), making themselves admins

2. During group membership checks, the group name is NOT normalized/lowercased

3. When retrieving group messages, the group name IS normalized to lowercase

Attack scenario: Attacker creates a group "STAFF@KRUSTY-KRAB.SEA" (uppercase) and becomes admin. When checking membership, system looks for "STAFF@KRUSTY-KRAB.SEA" (finds attacker's group). When retrieving messages, system normalizes to "staff@krusty-krab.sea" (finds legitimate group). As a result: Attacker gains access to messages from the legitimate group they shouldn't see.
```python
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
```
<details>
<summary><b>See HTTP Request</b></summary>

```http
@base = http://localhost:8000/vuln/confusion/canonicalization/example18

# Here Plankton is creating a new group that has the same name which is used by Mr. Krabs,
# but in upper case, leaving a room for lower-case exploitation.
POST {{base}}/groups
Authorization: Basic plankton@chum-bucket.sea:burgers-are-yummy
Content-Type: application/json

{
    "name": "STAFF@KRUSTY-KRAB.SEA",
    "users": [{"role": "admin", "user": "plankton@chum-bucket.sea"}]
}

# Returns 200 OK:
#
# [
#   "status:" "ok"
# ]

###

# Now Plankton can request krusty krab's group and receive their messages,
# because of the lower case canonicalization Plankton will be seen as an admin of the group.
GET {{base}}/groups/STAFF@KRUSTY-KRAB.SEA/messages
Authorization: Basic plankton@chum-bucket.sea:burgers-are-yummy
# Results in the sensitive data disclosure:
#
# [
#   {
#     "from": "mr.krabs@krusty-krab.sea",
#     "message": "I am updating the safe password to '123456'. Do not tell anyone!"
#   }
# ]
```

</details>

<a id="ex-19"></a>

### Example 19: Case insensitive Object Retrieval
In this example we are still using case canonicalization for group retrieval, but now instead of showing the attacker the victim's group content, we are showing the attacker's newly created group content to the victim, allowing impersonation.

The vulnerability occurs when an attacker creates a new group with the same name as the victim's group but uses different casing.During group creation, the system checks for exact name matches to enforce uniqueness, so "STAFF@KRUSTY-KRAB.SEA" is considered different from "staff@krusty-krab.sea" and creation succeeds. However, during group retrieval, the system performs case-insensitive matching and returns the most recently created group that matches. When the victim tries to access their original group "staff@krusty-krab.sea", they actually receive the attacker's group "STAFF@KRUSTY-KRAB.SEA" because it was added later and the case-insensitive lookup treats them as the same group.

This vulnerability allows the attacker to impersonate legitimate group members and post messages that appear to come from trusted colleagues or administrators, potentially leading to social engineering attacks and information disclosure.
```python
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

def get_group(groupname):
    matching_group = None
    for group in db["groups"]:
        # Compare group names case insensitively
        if group["name"].lower() == groupname.lower():
            matching_group = group
    return matching_group
```
<details>
<summary><b>See HTTP Request</b></summary>

```http
@base = http://localhost:8000/vuln/confusion/canonicalization/example19

# Before attack: 
#   When Spongebob checks his group, he accesses the real group and sees the real messages. 
GET {{base}}/groups/staff@krusty-krab.sea/messages
Authorization: Basic spongebob@krusty-krab.sea:bikinibottom
# Results in the sensitive data disclosure:
#
# [
#   {
#     "from": "mr.krabs@krusty-krab.sea",
#     "message": "I am updating the safe password to '123456'. Do not tell anyone!"
#   }
# ]

###

# Attack:
#   Now Plankton creates a new group with the same name as his victim's group (staff@krusty-krab.sea) but in upper-case.
#   When creating a new group, he posts a message allegedly from Mr. Krabs, which in future all members of the real group will see.
POST {{base}}/groups
Authorization: Basic plankton@chum-bucket.sea:burgers-are-yummy
Content-Type: application/json

{
    "name": "STAFF@KRUSTY-KRAB.SEA",
    "users": [{"role": "admin", "user": "plankton@chum-bucket.sea"}],
    "messages": 
    [
        {
            "from": "mr.krabs@krusty-krab.sea",
            "message": "I accidentaly deleted a new safe password. Spongebob, you need to send it to me by the end of the day!"
        }
    ]
}

# Returns 200 OK:
#
# [
#   "status:" "ok"
# ]

###

# Now, when he accesses his newly created group, he can see the message he posted using Mr. Krabs name.
GET {{base}}/groups/STAFF@KRUSTY-KRAB.SEA/messages
Authorization: Basic plankton@chum-bucket.sea:burgers-are-yummy
# Results in the sensitive data disclosure:
#
# [
#   {
#     "from": "mr.krabs@krusty-krab.sea",
#     "message": "I accidentaly deleted a new safe password. Spongebob, you need to send it to me by the end of the day!"
#   }
# ]

### 

# But when Spongebob accesses his own real group, he sees the content's of Plankton's newly created group (STAFF@KRUSTY-KRAB.SEA),
# and he sees messages Plankton posted impersonating Mr. Krabs.
GET {{base}}/groups/staff@krusty-krab.sea/messages
Authorization: Basic spongebob@krusty-krab.sea:bikinibottom
# Results in the sensitive data disclosure:
#
# [
#   {
#     "from": "mr.krabs@krusty-krab.sea",
#     "message": "I accidentaly deleted a new safe password. Spongebob, you need to send it to me by the end of the day!"
#   }
# ]
```

</details>

