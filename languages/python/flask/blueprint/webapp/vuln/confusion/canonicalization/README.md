# Canonicalization Confusion Vulnerabilities in Flask
This directory contains examples demonstrating various patterns of canonicalization confusion vulnerabilities in Flask applications. These examples show how inconsistent canonicalization can lead to security vulnerabilities.
## Overview

Canonicalization is the process of transforming data into a "standard" form, for example, when you paste your email with the first upper case letter most of the email providers will convert it to the lower case, e.g. "Example@mail.com" -> "example@mail.com".

Canonicalization confusion occurs when an application uses the canonical form inconsistently, for example, it might be only used when accessing data but not during the security checks.

## Table of Contents

| Category | Example | File |
|:---:|:---:|:---:|
| Lowercase Transformation | [Example 18: Lowercase Normalization](#ex-18) | [r01_lowercase/routes.py](r01_lowercase/routes.py#L27-L40) |

## Lowercase Transformation
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

