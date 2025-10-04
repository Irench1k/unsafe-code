# HTTP Semantics Confusion in Flask
We lean on verbs like GET and POST to signal how a request should behave, but Flask will parse bodies on any method, so a mismatched assumption can sneak past the guard.
## Overview

REST conventions say "GET requests have no body" and "POST carries form data." Flask allows clients to send any combination. If authorization logic relies on method-specific expectations (`request.args` for GET, `request.form` for POST), attackers can choose the code path that skips enforcement while still triggering state changes.

**Checklist:** - Explicitly branch on `request.method` before trusting where parameters come from. - Disallow unexpected bodies (`GET` with form data) when they bypass validation. - Keep idempotent and mutating logic separated; otherwise a GET with a body can act as a privileged POST.

The current example remains under `confusion/parameter_source/` until we migrate the source code.

## Table of Contents

| Category | Example | File |
|:---:|:---:|:---:|
| Method-Body Assumption Bypass | [Example 17: HTTP Method Confusion — GET With Body Triggers Update Without Auth](#ex-17) | [routes.py](routes.py#L31-L64) |

## Method-Body Assumption Bypass
A combined GET/POST controller assumes each method uses distinct parameter sources, letting a crafted GET body post messages as another user.
<a id="ex-17"></a>

### Example 17: HTTP Method Confusion — GET With Body Triggers Update Without Auth
A complicated controller for a groups API. Lists groups, returns group messages and posts new messages to a group.

The code processes both GET and POST requests, but lacks explicit method checks. This introduces a vulnerability due to incorrect assumptions.

The group membership check is performed in the `@check_group_membership` decorator, which checks the `group` argument – if present – in the request.values. The developer intent was to support passing the `group` argument via query string in GET requests, as well as via form argument in POST requests, and also support GET requests without the `group` argument.

However, since the code does not enforce this and lacks explicit method checks, it also supports GET requests with the `group` argument in the form body (Flask supports GET requests with the body, and will parse this data in `request.form` by default).

At the same time, `request.values` used in the `@check_group_membership` decorator ignores the form data on GET requests, leading to a confusion vulnerability.
```python
@bp.route("/example17/groups", methods=["GET", "POST"])
@basic_auth
@check_group_membership
def example17():
    """
    Groups controller. Lists groups, returns group messages and posts new messages to a group.

    GET requests:
      - without additional arguments, lists the groups the user is a member of
      - with a \`group\` query argument, returns the messages from the specified group

    POST requests:
      - with a \`group\` and \`message\` form argument, posts a new message to the specified group

    Authorization: A user can only access and post to groups they are a member of!

    GET  /groups                             -> list of groups the user is a member of
    GET  /groups?group=staff@krusty-krab.sea -> messages from the staff group, if the user is a member of the group
    POST /groups                             -> posts a new message to the specified group
    """
    if 'group' in request.form and 'message' in request.form:
        # POST /example17/groups
        # Content-Type: application/x-www-form-urlencoded
        #
        # group=staff@krusty-krab.sea&message=<message text>
        post_message_to_group(g.user, request.form.get("group"), request.form.get("message"))
        return {"status": "success"}

    if 'group' in request.args:
        # GET /example17/groups?group=staff@krusty-krab.sea
        return get_group_messages(request.args.get("group"))

    # GET /example17/groups
    return list_user_groups(g.user)

def check_group_membership(f):
    @wraps(f)
    def decorated_check_group_membership(*args, **kwargs):
        group = request.values.get("group")

        if group and not is_group_member(g.user, group):
            return "Forbidden: not an member for the requested group", 403

        return f(*args, **kwargs)
    return decorated_check_group_membership
```
<details>
<summary><b>See HTTP Request</b></summary>

```http
@base = http://localhost:8000/confusion/parameter-source/example17

# Without any arguments, GET request lists the groups the user is a member of
GET {{base}}/groups
Authorization: Basic plankton@chum-bucket.sea:burgers-are-yummy
# Returns 200 OK:
#
# [
#   "staff@krusty-krab.sea"
# ]

###

# With a \`group\` query argument, GET request returns the messages from the specified group
GET {{base}}/groups?group=staff@chum-bucket.sea
Authorization: Basic plankton@chum-bucket.sea:burgers-are-yummy
# Returns 200 OK:
#
# [
#   {
#     "from": "plankton@chum-bucket.sea",
#     "message": "To my future self, don't forget to steal the formula!"
#   }
# ]

###

# A POST request lets the user post a new message to the group where they are a member
POST {{base}}/groups
Authorization: Basic plankton@chum-bucket.sea:burgers-are-yummy
Content-Type: application/x-www-form-urlencoded

group=staff@chum-bucket.sea&message=If only I could steal employees from Krusty Krab...
# Returns 200 OK:
#
# {
#   "status": "success"
# }
#
# (The previous request now will show two messages for the staff@chum-bucket.sea group)

###

# Plankton should not able to post a new message to the Krusty Krab's group
POST {{base}}/groups
Authorization: Basic plankton@chum-bucket.sea:burgers-are-yummy
Content-Type: application/x-www-form-urlencoded

group=staff@krusty-krab.sea&message=Come, work for me at Chum Bucket!
# Returns 403 Forbidden error:
#
# Forbidden: not an member for the requested group

###

# However, due to the method confusion, Plankton can bypass this check by sending a GET request with the form body
GET {{base}}/groups
Authorization: Basic plankton@chum-bucket.sea:burgers-are-yummy
Content-Type: application/x-www-form-urlencoded

group=staff@krusty-krab.sea&message=Hey employees, it's me Krabs! My safe got rusty and needs to be repaired, please keep it open over night!
# Returns 200 OK:
#
# {
#   "status": "success"
# }

###

# Verify that the message was posted, using SpongeBob's credentials
GET {{base}}/groups?group=staff@krusty-krab.sea
Authorization: Basic spongebob@krusty-krab.sea:bikinibottom
# Returns 200 OK:
#
# [
#   {
#     "from": "mr.krabs@krusty-krab.sea",
#     "message": "I am updating the safe password to '123456'. Do not tell anyone!"
#   },
#   {
#     "from": "plankton@chum-bucket.sea",
#     "message": "Hey employees, it's me Krabs! My safe got rusty and needs to be repaired, please keep it open over night!"
#   }
# ]
```

</details>

