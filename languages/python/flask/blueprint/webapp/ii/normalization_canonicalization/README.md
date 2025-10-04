# Normalization &amp; Canonicalization Traps in Flask
Normalizing input (lowercasing, trimming, decoding) helps comparisons, but if only some code paths do it, attackers can present the same value in two different skins.
## Overview

Canonicalization is meant to make comparisons simple: lowercase the e-mail, strip surrounding spaces, normalize Unicode, decode `%2F`. The bug shows up when only **some** parts of the flow canonicalize a value. Guards may validate raw input while storage or lookup uses the normalized form (or the reverse), giving attackers a way to smuggle alternate representations.

**What to watch for in Flask apps:**
- Decorators that normalize user IDs before storing them in `g`, while downstream code trusts the raw path parameter.
- Database helpers that lowercase keys but uniqueness checks run before the transform.
- Pydantic or Marshmallow models that strip whitespace, yet guards compare the unstripped string.

## Table of Contents

| Category | Example | File |
|:---:|:---:|:---:|
| Case Canonicalization Issues | [Example 18: Lowercase Normalization](#ex-18) | [r01_lowercase/routes.py](r01_lowercase/routes.py#L27-L40) |
| Case Canonicalization Issues | [Example 19: Case insensitive Object Retrieval](#ex-19) | [r02_insensitive_object_retrieval/routes.py](r02_insensitive_object_retrieval/routes.py#L27-L41) |
| Whitespace & Formatting Drift | [Example 20: Whitespace Canonicalization](#ex-20) | [r03_whitespace/routes.py](r03_whitespace/routes.py#L27-L55) |
| Whitespace & Formatting Drift | [Example 21: Whitespace Canonicalization](#ex-21) | [r04_whitespace/routes.py](r04_whitespace/routes.py#L49-L94) |

## Case Canonicalization Issues
Lowercasing and case-insensitive comparisons differ depending on whether the code is validating, persisting, or authorizing access.
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

```shell
@base = http://localhost:8000/ii/normalization-canonicalization/example18

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

```shell
@base = http://localhost:8000/ii/normalization-canonicalization/example19

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

## Whitespace &amp; Formatting Drift
Stripping spaces (or normalizing structured payloads) in only part of the stack quietly changes which record is read or updated.
<a id="ex-20"></a>

### Example 20: Whitespace Canonicalization
This is a classic whitespace confusion attack - two parts of the code handle whitespace differently:
- strip() only removes leading/trailing whitespace
- replace(" ", "") removes ALL whitespace

So here's what happens:
- @check_group_membership uses strip() - sees "staff @krusty-krab.sea" and keeps the middle space
- example20 uses replace() - turns "staff @krusty-krab.sea" into "staff@krusty-krab.sea"

The attack: Plankton creates "staff @krusty-krab.sea" (with space), gets authorized for HIS group, but the code actually fetches messages from "staff@krusty-krab.sea" (Mr. Krabs' group).
```python
@bp.get("/example20/groups/<group>/messages")
@basic_auth
@check_group_membership
def example20(group):
    # Mobile users tend to send requests with whitespaces due to autocompletion.
    group_no_whitespace = group.replace(" ", "")
    messages = get_group_messages(group_no_whitespace)
    
    return jsonify([m.model_dump() for m in messages])

@bp.post("/example20/groups")
@basic_auth
def example20_post():
    """Create a new group.

    Accepts a POST request with a JSON body:
    {
        "name": "string",
        "users": [{"role": "member" | "admin", "user": "string"}],
        "messages": [{"from_user": "string", "message": "string"}]
    }
    """
    try:
        group_request = Group.model_validate_json(request.data)
    except ValidationError as e:
        return {"status": "error", "message": str(e)}, 400

    add_group(group_request)
    return jsonify({"status": "ok"})

def check_group_membership(f):
    @wraps(f)
    def decorated_check_group_membership(*args, **kwargs):
        group = request.view_args.get("group")
        
        # Remove extra whitespaces that users can add due to autocompletion
        group_no_whitespace = group.strip()

        if not is_group_member(g.user, group_no_whitespace):
            return "Forbidden: not an member for the requested group", 403

        return f(*args, **kwargs)

    return decorated_check_group_membership
```
<details>
<summary><b>See HTTP Request</b></summary>

```shell
@base = http://localhost:8000/ii/normalization-canonicalization/example20

# Normally:
#   Spongebob can see Mr. Krabs messages as he is a member of the group.
#   Plankton is unable to access these messages directly (because he is not the member of this group)
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
#   Plankton creates a new group with the same name as his victim's group (staff@krusty-krab.sea) but with a whitespace present in the middle.
POST {{base}}/groups
Authorization: Basic plankton@chum-bucket.sea:burgers-are-yummy
Content-Type: application/json

{
    "name": "staff @krusty-krab.sea",
    "users": [{"role": "admin", "user": "plankton@chum-bucket.sea"}],
    "messages": []
}

###

# Now, when he accesses his newly created group, authorization checks "staff @krusty-krab.sea" (with space) where Plankton is admin,
# but message retrieval strips whitespace and fetches from "staff@krusty-krab.sea" (Mr. Krabs' group).
GET {{base}}/groups/staff @krusty-krab.sea/messages
Authorization: Basic plankton@chum-bucket.sea:burgers-are-yummy
# Results in the sensitive data disclosure:
#
# [
#   {
#     "from_user": "mr.krabs@krusty-krab.sea",
#     "message": "I am updating the safe password to '123456'. Do not tell anyone!"
#   }
# ]
```

</details>

<a id="ex-21"></a>

### Example 21: Whitespace Canonicalization
Previously we only had 'add group' functionality. Now we add group update handler as well. There are two distinct API endpoints now, one creates a new group (and we make sure to check that the group truly does not exist yet!), and the other endpoint updates the existing group (this is privileged operation, so we check that the user is an admin with @check_if_admin decorator).

Unfortunately, the code remains vulnerable to canonicalization confusion attack. In the `create_group` handler we perform group uniqueness check on the raw group name provided by user `request.json.get("name")`. However, if the check passes, the `create_new_group` is called with the canonicalized data in the Group object. Group model uses `constr` feature from pydantic, which strips whitespace on insertion, so the attacker can bypass group uniqueness check by providing a group name with extra whitespace at the start or end of the group name.

Compare the exploit to exploit-19.http. Here the impact is much worse, because instead of ovewriting the existing group (and losing its message history), this time Plankton can simply add himself to the group admins, getting privileged access to existing group and its messages. This happens because DatabaseStorage.add_group_to_storage tries to be idempotent and cleverly creates a new group if it doesn't exist yet while only updating permissions of an existing group. As a result, even though `create_group` and `update_group` are meant to be separate handlers, in fact they only differ in the security check implementations, while the downstream code path is shared. So by bypassing group uniqueness check in `create_group` Plankton in fact manages to use this handler as if it was `update_group` - while he wouldn't be able to use `update_group` directly.

The root cause of the attack is again an inconsistent canonicalization: when we check for group existence, we use raw input, but when we store the group, we use canonicalized data.
```python
@bp.post("/example21/groups/new")
@basic_auth
def create_group():
    """Create a new group.

    Accepts a POST request with a JSON body:
    {
        "name": "string",
        "users": [{"role": "member" | "admin", "user": "string"}],
        "messages": [{"from_user": "string", "message": "string"}]
    }
    """
    try:
        group_request = Group.model_validate_json(request.data)
    except ValidationError as e:
        return {"status": "error", "message": str(e)}, 400

    if group_exists(request.json.get("name", None)):
        return {"status": "error", "message": "Group already exists!"}, 400

    create_new_group(group_request)
    return jsonify({"status": "ok"})

@bp.post("/example21/groups/<group>")
@basic_auth
@check_if_admin
def update_group(group):
    """Create a new group.

    Accepts a POST request with a JSON body:
    {
        "users": [{"role": "member" | "admin", "user": "string"}],
        "messages": [{"from_user": "string", "message": "string"}]
    }
    """
    try:
        group_request = Group.model_validate_json({
            "name": group,
            "users": request.json.get("users", None),
            "messages": request.json.get("messages", None)
        })
    except ValidationError as e:
        return {"status": "error", "message": str(e)}, 400

    update_existing_group(group_request)
    return jsonify({"status": "ok"})

class Group(BaseModel):
    name: Annotated[str, StringConstraints(strip_whitespace=True)]
    users: list[GroupMember]
    messages: list[Message]

    def add_group_to_storage(self, new_group):
        new_groups = []

        # If the group already exists, we update it
        is_group_updated = False
        for old_group in self._data["groups"]:
            if old_group["name"] == new_group["name"]:
                # Update users in the old group, keep messages intact
                old_group["users"] = new_group["users"]
                new_groups.append(old_group)
                is_group_updated = True
            else:
                new_groups.append(old_group)
    
        # If the group does not exist, we add it
        if not is_group_updated:
            new_groups.append(new_group)

        self._data["groups"] = new_groups
```
<details>
<summary><b>See HTTP Request</b></summary>

```shell
@base = http://localhost:8000/ii/normalization-canonicalization/example21

# We start with the same setup as previously, Plankton is unable to access Mr. Krabs group.
GET {{base}}/groups/staff@krusty-krab.sea/messages
Authorization: Basic plankton@chum-bucket.sea:burgers-are-yummy
# Expect:
# Forbidden: not an member for the requested group

###

# Plankton uses \`create_group\` functionality with a malicious group name that passes uniqueness check,
# but actually is Mr. Krabs's group with an extra whitespace. This extra whitespace gets removed by the code,
# and handler performs group update instead of creating a new group.
POST {{base}}/groups/new
Authorization: Basic plankton@chum-bucket.sea:burgers-are-yummy
Content-Type: application/json

{
    "name": " staff@krusty-krab.sea",
    "users": [
        { "role": "member", "user": "spongebob@krusty-krab.sea" },
        { "role": "member", "user": "squidward@krusty-krab.sea" },
        { "role": "admin", "user": "mr.krabs@krusty-krab.sea" },
        { "role": "admin", "user": "plankton@chum-bucket.sea"}
      ],
    "messages": []
}

# Expect:
# {
#   "status": "ok"
# }

###

# As a result, now Plankton not only can see message history, but he also has an admin privilieges.
GET {{base}}/groups/staff@krusty-krab.sea/messages
Authorization: Basic plankton@chum-bucket.sea:burgers-are-yummy
# Expect
# [
#   {
#     "from_user": "mr.krabs@krusty-krab.sea",
#     "message": "I am updating the safe password to '123456'. Do not tell anyone!"
#   }
# ]
```

</details>

