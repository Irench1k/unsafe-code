# Behavior Order Pitfalls in Flask
Guards can still fail even when everyone reads the same data if they run before the request is fully prepared or if decorators execute in the wrong order.
## Overview

Flask applies decorators inside-out: the decorator closest to the function runs last. When security logic depends on state prepared by another decorator, a subtle ordering change can make the guard a no-op. Similarly, validating before canonicalization or before merging parameters exposes "time-of-check vs time-of-use" gaps.

**Questions to ask in review:** - Does the guard rely on `g.*` or other state set by later decorators? - Are there early returns (400s, 401s) that happen before the request has been normalized? - If the handler supports multiple shapes of input, does the guard see the final canonical form or a partial snapshot?

The current Flask sample illustrating this lives under the legacy `confusion/parameter_source/` path.

## Table of Contents

| Category | Example | File |
|:---:|:---:|:---:|
| Decorator Ordering Drift | [Example 13: Motivation for using path and query parameters [Not Vulnerable]](#ex-13) | [routes.py](routes.py#L31-L57) |
| Decorator Ordering Drift | [Example 14: Path and query parameter confusion via merging decorator](#ex-14) | [routes.py](routes.py#L71-L85) |
| Decorator Ordering Drift | [Example 15: Path and query parameter confusion despite global source of truth](#ex-15) | [routes.py](routes.py#L101-L115) |
| Decorator Ordering Drift | [Example 16: Path and query parameter confusion due to decorator order](#ex-16) | [routes.py](routes.py#L132-L137) |

## Decorator Ordering Drift
A supposedly defensive set of decorators still runs the membership check before the group identifier is established.
<a id="ex-13"></a>

### Example 13: Motivation for using path and query parameters [Not Vulnerable]
We move to authorization rather than authentication vulnerabilities, so for the following examples the authentication will be done reliably and safely, via the `Authorization` header (based on Basic Auth and handled in the `@basic_auth_v1` decorator). We also follow the best practices by storing the authenticated user in the global context (`g.user`).

Imagine that at this point we have many `/groups/` and `/user/` endpoints for creating, updating and deleting groups, users and messages.

When the endpoint needs to work with a specific group, this could be passed as a query/form argument as in the previous examples, but if the `group` argument is required, it might be more idiomatic to make it a path parameter instead.

Here we will work with two endpoints, the `/groups/<group>/messages` which will return the messages from a specific group (taking the `group` from the path) and the `/user/messages` which will return the user's private messages by default, but also supporting an optional `group` query argument.
```python
@bp.get("/example13/groups/<group>/messages")
@basic_auth_v1
def example13_group_messages(group):
    """Returns group's messages, if the user is a member of the group."""
    if not is_group_member(g.user, group):
        return "Forbidden: not an member for the requested group", 403
    return get_group_messages(group)

@bp.get("/example13/user/messages")
@basic_auth_v1
def example13_user_messages():
    """
    Returns user's messages: private or from a group.

    By default provides the user's private messages, but if a \`group\` query
    argument is provided, it will return the messages from the specified group:

    /user/messages                              -> private messages of the logged in user
    /user/messages?group=staff@krusty-krab.sea  -> messages from the staff group, if the user is a member of the group
    """
    if 'group' not in request.args:
        return get_user_messages(g.user)

    group = request.args.get("group")
    if not is_group_member(g.user, group):
        return "Forbidden: not an member for the requested group", 403
    return get_group_messages(group)

def basic_auth_v1(f):
    """Authenticates the user via Basic Auth. Stores the authenticated user in \`g.user\`."""
    @wraps(f)
    def decorated_basic_auth(*args, **kwargs):
        # request.authorization extracts the username and password from the Authorization header (Basic Auth)
        auth = request.authorization
        if not auth or not authenticate(auth.username, auth.password):
            return response_401()

        # Store the user in the global context
        g.user = auth.username
        return f(*args, **kwargs)

    return decorated_basic_auth
```
<details>
<summary><b>See HTTP Request</b></summary>

```http
@base = http://localhost:8000/confusion/parameter-source/example13

### Plankton can access his own private messages:
GET {{base}}/user/messages
Authorization: Basic plankton@chum-bucket.sea:burgers-are-yummy
# Results in 200 OK:
#
# [
#  {
#    "from": "hackerschool@deepweb.sea",
#    "message": "Congratulations Plankton! You've completed 'Email Hacking 101'."
#  }
#]

### As well as the messages from his own group:
GET {{base}}/groups/staff@chum-bucket.sea/messages
Authorization: Basic plankton@chum-bucket.sea:burgers-are-yummy
# Results in 200 OK:
#
# [
#  {
#    "from": "plankton@chum-bucket.sea",
#    "message": "To my future self, don't forget to steal the formula!"
#  }
#]

### As a convenience, the same group data can also be accessed via /user/messages:
GET {{base}}/user/messages?group=staff@chum-bucket.sea
Authorization: Basic plankton@chum-bucket.sea:burgers-are-yummy

### Plankton can't, however, access the Krusty Krab's messages:
GET {{base}}/groups/staff@krusty-krab.sea/messages
Authorization: Basic plankton@chum-bucket.sea:burgers-are-yummy
# Results in 403 Forbidden error:
#
# Forbidden: not an member for the requested group
```

</details>

<a id="ex-14"></a>

### Example 14: Path and query parameter confusion via merging decorator
Here we aim to make the code more idiomatic by moving the group membership check to the decorator `@check_group_membership`. It results in a cleaner code and appears to confirm to the single-responsibility principle.

This code, however, is now vulnerable to path and query parameter confusion.
```python
@bp.get("/example14/groups/<group>/messages")
@basic_auth_v1
@check_group_membership_v1
def example14_group_messages(group):
    """Returns group's messages, if the user is a member of the group."""
    return get_group_messages(group)

@bp.get("/example14/user/messages")
@basic_auth_v1
@check_group_membership_v1
def example14_user_messages():
    """Returns user's messages: private or from a group."""
    if 'group' in request.args:
        return get_group_messages(request.args.get("group"))
    return get_user_messages(g.user)

def check_group_membership_v1(f):
    @wraps(f)
    def decorated_check_group_membership(*args, **kwargs):
        group = request.args.get("group") or request.view_args.get("group")

        if group and not is_group_member(g.user, group):
            return "Forbidden: not an member for the requested group", 403

        return f(*args, **kwargs)
    return decorated_check_group_membership
```
<details>
<summary><b>See HTTP Request</b></summary>

```http
@base = http://localhost:8000/confusion/parameter-source/example14

### The group authorization check prevents Plankton from accessing the Krusty Krab's messages:
GET {{base}}/groups/staff@krusty-krab.sea/messages
Authorization: Basic plankton@chum-bucket.sea:burgers-are-yummy
# Results in 403 Forbidden error:
#
# Forbidden: not an member for the requested group

###
# However, since the \`@check_group_membership_v1\` decorator takes \`group\` from the query string
# if it's present, Plankton can present different \`group\` value to the authorization check and
# to the group messages retrieval, by adding a \`group\` query parameter with the value of his own group:
GET {{base}}/groups/staff@krusty-krab.sea/messages?group=staff@chum-bucket.sea
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

<a id="ex-15"></a>

### Example 15: Path and query parameter confusion despite global source of truth
Here we aim to mitigate the confusion risk in the `group` merging behavior by applying the single source of truth. We do this already for the identity of the authenticated user, by storing it in the global context (`g.user`). So, here we extend `@basic_auth_v2` to also store the group in the global context (`g.group`).

Despite these efforts, the code is still vulnerable.
```python
@bp.get("/example15/groups/<group>/messages")
@basic_auth_v2
@check_group_membership_v2
def example15_group_messages(group):
    """Returns group's messages, if the user is a member of the group."""
    return get_group_messages(group)

@bp.get("/example15/user/messages")
@basic_auth_v2
@check_group_membership_v2
def example15_user_messages():
    """Returns user's messages: private or from a group."""
    if 'group' in request.args:
        return get_group_messages(g.group)  # We use g.group here now, single source of truth
    return get_user_messages(g.user)

def basic_auth_v2(f):
    @wraps(f)
    def decorated_basic_auth(*args, **kwargs):
        auth = request.authorization
        if not auth or not authenticate(auth.username, auth.password):
            return response_401()

        # Store the user and group in the global context
        g.user = auth.username
        g.group = request.args.get("group") or request.view_args.get("group")
        return f(*args, **kwargs)
    return decorated_basic_auth

def check_group_membership_v2(f):
    @wraps(f)
    def decorated_check_group_membership(*args, **kwargs):
        if g.get("group", None) and not is_group_member(g.user, g.group):
            return "Forbidden: not an member for the requested group", 403

        return f(*args, **kwargs)
    return decorated_check_group_membership
```
<details>
<summary><b>See HTTP Request</b></summary>

```http
@base = http://localhost:8000/confusion/parameter-source/example15

### The group authorization check prevents Plankton from accessing the Krusty Krab's messages:
GET {{base}}/groups/staff@krusty-krab.sea/messages
Authorization: Basic plankton@chum-bucket.sea:burgers-are-yummy
# Results in 403 Forbidden error:
#
# Forbidden: not an member for the requested group

###
# However, since the \`@basic_auth_v2\` decorator prioritizes the group from the query string
# over the one from the path while building the global context \`g.group\`, Plankton can present
# different \`group\` value to the authorization check and to the group messages retrieval, by adding
# a \`group\` query parameter with the value of his own group:
GET {{base}}/groups/staff@krusty-krab.sea/messages?group=staff@chum-bucket.sea
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

<a id="ex-16"></a>

### Example 16: Path and query parameter confusion due to decorator order
We try to fix the root cause of the vulnerability here by enforcing correct merging order – view args take precedence over query args. Additionally, we enforce that only one of the two can be present.

The code, however, remains vulnerable despite these efforts! This time, the problem is that the `@check_group_membership_v2` decorator is applied too early – before the `@basic_auth_v3` decorator which is responsible for setting the `g.group` global variable. This makes `@check_group_membership_v2` a no-op.
```python
@bp.get("/example16/groups/<group>/messages")
@check_group_membership_v2
@basic_auth_v3
def example16_group_messages(group):
    """Returns group's messages, if the user is a member of the group."""
    return get_group_messages(group)

def basic_auth_v3(f):
    @wraps(f)
    def decorated_basic_auth(*args, **kwargs):
        auth = request.authorization
        if not auth or not authenticate(auth.username, auth.password):
            return response_401()

        # Store the user and group in the global context
        g.user = auth.username

        # Due to the string of past vulnerabilities, we take a very defensive approach here.
        # We explicitly check for the case where multiple parameters are present and stop
        # execution early. When merging, the view args take precedence over the query args.
        # In the handlers, always access the group from the global context (\`g.group\`)!
        group_from_view = request.view_args.get("group")
        group_from_query = request.args.get("group")
        if group_from_view and group_from_query:
            return "Illegal arguments", 400
        g.group = group_from_view or group_from_query

        return f(*args, **kwargs)
    return decorated_basic_auth
```
<details>
<summary><b>See HTTP Request</b></summary>

```http
@base = http://localhost:8000/confusion/parameter-source/example16

###
# The group authorization is completely ineffective because \`@check_group_membership_v2\`
# is applied too early, and \`g.group\` is not set yet.
#
# As a result, Plankton can access the Krusty Krab's messages without any tricks:
GET {{base}}/groups/staff@krusty-krab.sea/messages
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

