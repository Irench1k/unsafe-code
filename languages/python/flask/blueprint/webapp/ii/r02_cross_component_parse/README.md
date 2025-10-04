# Cross-Component Parsing Drift in Flask

Decorators, middleware, and helpers sometimes grab request data before the view does; if each layer resolves parameters differently, the same call holds two meanings.

## Overview

Flask's architecture allows each layer (decorators, middleware, before-request hooks, views) to independently choose how to source request data from multiple APIs: `request.args`, `request.form`, `request.values`, or `request.view_args`. When layers use different APIs or apply different merging strategies (e.g., args-priority vs form-priority), the same HTTP request carries multiple semantic interpretations. The guard validates one parameter value while the handler acts on another, enabling authorization bypasses even when all components execute in correct order.

**Spotting the issue:**
- Audit every decorator or middleware applied to a route and see which request APIs they touch (`request.args` vs `request.form` vs `request.values` vs `request.view_args`).
- Check for custom merging logic that prioritizes sources differently (e.g., `request.args or request.view_args` vs direct function parameter binding).
- Be suspicious when global state (e.g. `g.*`) is set in one layer but components still access raw request sources directly.
- Verify decorators and handlers agree on which parameter source is authoritative for security decisions.

## Table of Contents

| Category | Example | File |
|:---:|:---:|:---:|
| Shared Contract Baseline | [Example 13: Shared Contract Baseline [Not Vulnerable]](#ex-13) | [r01_baseline/routes.py](r01_baseline/routes.py#L31-L57) |
| Decorators That Drift | [Example 8: Decorator-based Authentication with Parsing Drift](#ex-8) | [r02_decorator_drift/routes.py](r02_decorator_drift/routes.py#L19-L25) |
| Decorators That Drift | [Example 14: Path and query parameter confusion via merging decorator](#ex-14) | [r02_decorator_drift/routes.py](r02_decorator_drift/routes.py#L43-L57) |
| Decorators That Drift | [Example 15: Path and query parameter confusion despite global source of truth](#ex-15) | [r02_decorator_drift/routes.py](r02_decorator_drift/routes.py#L76-L90) |
| Middleware Short-Circuiting Views | [Example 9: Middleware-based Authentication with Parsing Drift](#ex-9) | [r03_middleware_drift/routes.py](r03_middleware_drift/routes.py#L22-L27) |

## Shared Contract Baseline

A safe reference flow where decorators and views agree on how the group identifier is sourced.

### Example 13: Shared Contract Baseline [Not Vulnerable] <a id="ex-13"></a>

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

```shell
@base = http://localhost:8000/ii/cross-component-parse/example13

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

## Decorators That Drift

Guards implemented as decorators merge or prioritize request data differently than the view, enabling bypasses.

### Example 8: Decorator-based Authentication with Parsing Drift <a id="ex-8"></a>

Shows how using decorators can obscure parameter source confusion.

Example 8 is functionally equivalent to Example 4 from the old parameter source confusion examples, but it may be harder to spot the vulnerability while using decorators.

The decorator authenticates using request.args.get("user"), but the handler retrieves the user via get_user() which prioritizes request.form over request.args.
```python
@bp.route("/example8", methods=["GET", "POST"])
@authentication_required
def example8():
    messages = get_messages_ex8(get_user_ex8())
    if messages is None:
        return "No messages found", 404
    return messages

def authentication_required(f):
    @wraps(f)
    def decorated_example8(*args, **kwargs):
        if not authenticate_ex8():
            return "Invalid user or password", 401
        return f(*args, **kwargs)

    return decorated_example8
```
<details>
<summary><b>See HTTP Request</b></summary>

```shell
@base = http://localhost:8000/ii/cross-component-parse

### Expected Usage:
GET {{base}}/example8?user=alice&password=123456
#
# Normally, Alice would get her *own* messages:
#
# {
#   "owner": "alice",
#   "messages": [
#     {
#       "from": "kevin",
#       "message": "Hi Alice, you're fired!"
#     }
#   ]
# }
#

###

### Attack: Decorator authenticates using query params, handler uses form data
GET {{base}}/example8?user=alice&password=123456
Content-Type: application/x-www-form-urlencoded

user=bob
#
# Alice gets Bob's messages, even though she provided her own password!
#
# {
#   "owner": "bob",
#   "messages": [
#     {
#       "from": "kevin",
#       "message": "Hi Bob, here is the password you asked for: P@ssw0rd!"
#     },
#     {
#       "from": "michael",
#       "message": "Hi Bob, come to my party on Friday! The secret passphrase is 'no-one-knows-it'!"
#     }
#   ]
# }
```

</details>

### Example 14: Path and query parameter confusion via merging decorator <a id="ex-14"></a>

Here we aim to make the code more idiomatic by moving the group membership check to the decorator `@check_group_membership`. It results in a cleaner code and appears to confirm to the single-responsibility principle.

This code, however, is now vulnerable to path and query parameter confusion. The decorator's merging logic (request.args or request.view_args) prioritizes query parameters, while Flask's URL routing binds path parameters directly to function arguments. An attacker can pass their group in the query string to bypass authorization while accessing a different group's data via the path.
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

def basic_auth_v1(f):
    """Authenticates the user via Basic Auth. Stores the authenticated user in \`g.user\`."""
    @wraps(f)
    def decorated_basic_auth(*args, **kwargs):
        # request.authorization extracts the username and password from the Authorization header (Basic Auth)
        auth = request.authorization
        if not auth or not authenticate_ex14(auth.username, auth.password):
            return response_401()

        # Store the user in the global context
        g.user = auth.username
        return f(*args, **kwargs)

    return decorated_basic_auth


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

```shell
@base = http://localhost:8000/ii/cross-component-parse/example14

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

### Example 15: Path and query parameter confusion despite global source of truth <a id="ex-15"></a>

Here we aim to mitigate the confusion risk in the `group` merging behavior by applying the single source of truth. We do this already for the identity of the authenticated user, by storing it in the global context (`g.user`). So, here we extend `@basic_auth_v2` to also store the group in the global context (`g.group`).

Despite these efforts, the code is still vulnerable. The decorator sets g.group with query-priority merging, but the handler function still receives the path parameter directly from Flask's routing. The handler passes this path parameter to get_group_messages(), ignoring g.group entirely in example15_group_messages.
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
        if not auth or not authenticate_ex14(auth.username, auth.password):
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

```shell
@base = http://localhost:8000/ii/cross-component-parse/example15

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

## Middleware Short-Circuiting Views

Before-request hooks authenticate on query parameters only, while views consume form data.

### Example 9: Middleware-based Authentication with Parsing Drift <a id="ex-9"></a>

Demonstrates how Flask's middleware system can contribute to parameter source confusion.

Example 9 is functionally equivalent to Example 4 from the old parameter source confusion examples, but it may be harder to spot the vulnerability while using middleware.

The before_request middleware authenticates using request.args.get("user"), but the handler retrieves the user via get_user(request) which prioritizes request.form over request.args. This allows an attacker to authenticate as Alice but access Bob's messages.
```python
@bp.route("/example9", methods=["GET", "POST"])
def example9():
    messages = get_messages(get_user(request))
    if messages is None:
        return "No messages found", 404
    return messages

def register_middleware(app):
    @app.before_request
    def verify_user():
        """Authenticate the user, based solely on the request query string."""
        if not authenticate(
            request.args.get("user", None), request.args.get("password", None)
        ):
            return "Invalid user or password", 401

        # In Flask, if the middleware returns non-None value, the value is handled as if it was
        # the return value from the view, and further request handling is stopped
        return None

    return verify_user
```
<details>
<summary><b>See HTTP Request</b></summary>

```shell
@base = http://localhost:8000/ii/cross-component-parse

### Expected Usage:
GET {{base}}/example9?user=alice&password=123456
#
# Normally, Alice would get her *own* messages:
#
# {
#   "owner": "alice",
#   "messages": [
#     {
#       "from": "kevin",
#       "message": "Hi Alice, you're fired!"
#     }
#   ]
# }
#

###

### Attack: Middleware authenticates using query params, handler uses form data
GET {{base}}/example9?user=alice&password=123456
Content-Type: application/x-www-form-urlencoded

user=bob
#
# Alice gets Bob's messages, even though she provided her own password!
#
# {
#   "owner": "bob",
#   "messages": [
#     {
#       "from": "kevin",
#       "message": "Hi Bob, here is the password you asked for: P@ssw0rd!"
#     },
#     {
#       "from": "michael",
#       "message": "Hi Bob, come to my party on Friday! The secret passphrase is 'no-one-knows-it'!"
#     }
#   ]
# }
```

</details>

