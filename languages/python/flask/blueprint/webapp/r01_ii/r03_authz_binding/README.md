# Authorization Binding Drift in Flask

Binding bugs happen when we authenticate one identity but later trust user-controlled parameters for the actual work, letting attackers act on behalf of someone else or access unintended resources.

## Overview

Authorization binding drift occurs when an application successfully authenticates WHO a user is, but then trusts user-controlled parameters to determine WHICH resource to act on or WHOSE identity to act as. This separates the security decision (authentication/authorization) from the action being taken.

**Key distinction from other inconsistent interpretation bugs:**
- **NOT source precedence**: We're not confusing parameter sources (args vs form). The authenticated identity is correctly established.
- **NOT parsing drift**: Different components don't parse differently. Authentication succeeds properly.
- **IS binding drift**: The authenticated identity (WHO) is correct, but user-controlled parameters rebind the resource (WHICH) or identity (AS WHOM) for the actual operation.

**Common patterns:**
1. **Resource rebinding**: Authenticate user X, authorize access to resource A, but action uses user-controlled resource B
2. **Identity rebinding**: Authenticate user X, authorize action on resource, but operation claims to be "from" user Y

In multi-tenant or multi-user APIs, a common pattern is to authenticate once (session, token, Basic Auth) and then trust request data to determine which account, tenant, or resource to act on. If the handler uses attacker-controlled identifiers after successful authentication - `request.json["owner"]`, `request.args["user_id"]`, path vs query confusion - it creates binding drift.

**When reviewing code:**
- Trace the authenticated identity from authentication → authorization → action
- Check if authorization decisions and actions use THE SAME identifier for resources
- Look for user-controlled parameters that determine resource IDs or identities AFTER authentication
- Verify that decorators and handlers don't apply different merging logic for resource identifiers
- Be suspicious of "from_user", "owner_id", "account_id" parameters after authentication succeeded

**Real-world scenarios:**
- Social media APIs where you can post "as" another user
- Multi-tenant apps where you authenticate as user X but can access tenant Y's data
- Group messaging where authentication checks one group but data comes from another
- Background job APIs that trust user-supplied "owner" fields

## Table of Contents

| Category | Example | File |
|:---:|:---:|:---:|
| Secure Authorization Baseline | [Example 13: Secure Authorization Binding Baseline [Not Vulnerable]](#ex-13) | [r01_baseline/routes.py](r01_baseline/routes.py#L28-L58) |
| Path-Query Confusion Leading to Binding Drift | [Example 14: Authorization Binding Drift via Path-Query Confusion](#ex-14) | [r02_path_query_confusion/routes.py](r02_path_query_confusion/routes.py#L35-L50) |
| Path-Query Confusion Leading to Binding Drift | [Example 15: Authorization Binding Drift Despite Global Source of Truth](#ex-15) | [r02_path_query_confusion/routes.py](r02_path_query_confusion/routes.py#L82-L97) |
| Classic Identity Rebinding | [Example 16: Classic Authorization Binding Drift - User Identity Rebinding](#ex-16) | [r03_simple_rebinding/routes.py](r03_simple_rebinding/routes.py#L39-L76) |

## Secure Authorization Baseline

The correct pattern for handling authorization binding: authenticate the user, establish their identity in global context (g.user), and consistently use the same source for resource identifiers in both authorization checks and data access. No user-controlled parameters can rebind resources after authorization succeeds.

### Example 13: Secure Authorization Binding Baseline [Not Vulnerable] <a id="ex-13"></a>

This demonstrates the correct way to handle authorization binding in a multi-user application. Authentication establishes WHO the user is, and authorization checks verify that the authenticated identity has access to the requested resource.

Key security properties:
- Authentication via Basic Auth establishes `g.user` (WHO)
- Authorization checks use the SAME source for the resource identifier (group parameter)
- The data retrieval also uses the SAME source for the resource identifier
- No user-controlled parameters can rebind the resource after authorization

This example provides two endpoints:
1. `/groups/<group>/messages` - Returns messages from a specific group (path parameter)
2. `/user/messages` - Returns user's private messages, or group messages if `group` query param provided

In both cases, the authorization check and the data access use the same source, preventing any binding drift attacks.
```python
@bp.get("/example13/groups/<group>/messages")
@basic_auth_v1
def example13_group_messages(group):
    """Returns messages from a specified group."""
    if not is_group_member(g.user, group):
        return "Forbidden: not a member of the requested group", 403

    return get_group_messages(group)


@bp.get("/example13/user/messages")
@basic_auth_v1
def example13_user_messages():
    """
    Returns user's private messages, or group messages if specified.

    Query parameters:
      - group (optional): Group identifier to retrieve messages from

    Examples:
      GET /user/messages                              → private messages
      GET /user/messages?group=staff@krusty-krab.sea  → group messages
    """
    if 'group' not in request.args:
        return get_user_messages(g.user)

    group = request.args.get("group")
    if not is_group_member(g.user, group):
        return "Forbidden: not a member of the requested group", 403

    return get_group_messages(group)

def basic_auth_v1(f):
    """
    Authenticates the user via Basic Auth.
    Stores the authenticated user in \`g.user\`.
    """
    @wraps(f)
    def decorated_basic_auth(*args, **kwargs):
        # request.authorization extracts the username and password from the Authorization header (Basic Auth)
        auth = request.authorization
        if not auth or not authenticate(auth.username, auth.password):
            return response_401()

        # Store the authenticated user in the global context
        g.user = auth.username
        return f(*args, **kwargs)

    return decorated_basic_auth
```
<details>
<summary><b>See HTTP Request</b></summary>

```shell
@base = http://localhost:8000/ii/authz-binding/example13

### Plankton can access his own group's messages
GET {{base}}/groups/staff@chum-bucket.sea/messages
Authorization: Basic plankton@chum-bucket.sea:burgers-are-yummy

# Results in 200 OK:
#
# [
#  {
#    "from": "plankton@chum-bucket.sea",
#    "message": "To my future self, don't forget to steal the formula!"
#  }
# ]

###

### As well as his private messages via the user endpoint:
GET {{base}}/user/messages
Authorization: Basic plankton@chum-bucket.sea:burgers-are-yummy

# Results in 200 OK:
#
# [
#  {
#    "from": "hackerschool@deepweb.sea",
#    "message": "Congratulations Plankton! You've completed 'Email Hacking 101'."
#  }
# ]

###

### Plankton can't, however, access the Krusty Krab's messages:
GET {{base}}/groups/staff@krusty-krab.sea/messages
Authorization: Basic plankton@chum-bucket.sea:burgers-are-yummy

# Results in 403 Forbidden error:
#
# Forbidden: not a member of the requested group

###

### SpongeBob can access his group's sensitive messages:
GET {{base}}/groups/staff@krusty-krab.sea/messages
Authorization: Basic spongebob@krusty-krab.sea:bikinibottom

# Results in 200 OK:
#
# [
#  {
#    "from": "mr.krabs@krusty-krab.sea",
#    "message": "I am updating the safe password to '123456'. Do not tell anyone!"
#  }
# ]
```

</details>

## Path-Query Confusion Leading to Binding Drift

Authorization binding drift caused by decorators that merge path and query parameters with inconsistent priority. The decorator checks authorization using one source (query parameters), but the handler accesses data using another source (path parameters), creating binding drift even though the authenticated identity is correct.

These examples show how parameter source merging creates binding drift between the authorization check (WHICH resource is authorized) and the action (WHICH resource is accessed).

### Example 14: Authorization Binding Drift via Path-Query Confusion <a id="ex-14"></a>

This example demonstrates authorization binding drift caused by a decorator that merges path and query parameters with query-priority.

THE VULNERABILITY: Authorization binding drift, NOT source precedence.
- Authentication establishes WHO: Plankton (verified identity)
- Authorization checks WHICH resource: staff@chum-bucket.sea (from query param)
- Action accesses DIFFERENT resource: staff@krusty-krab.sea (from path param)

The key insight: We know WHO Plankton is (authentication succeeded), but we allow him to control WHICH resource the authorization checks versus WHICH resource gets accessed.

Attack flow:
1. Plankton authenticates as himself (WHO = plankton@chum-bucket.sea) ✓
2. Authorization decorator checks access to staff@chum-bucket.sea (query param) ✓
3. Handler retrieves messages from staff@krusty-krab.sea (path param) ✗

This is binding drift because the authenticated identity is correct, but the resource identifier gets rebound between authorization and action.
```python
@bp.get("/example14/groups/<group>/messages")
@basic_auth_v1
@check_group_membership_v1
def example14_group_messages(group):
    """Returns messages from a specified group."""
    return get_group_messages(group)


@bp.get("/example14/user/messages")
@basic_auth_v1
@check_group_membership_v1
def example14_user_messages():
    """Returns user's private messages, or group messages if specified."""
    if 'group' in request.args:
        return get_group_messages(request.args.get("group"))
    return get_user_messages(g.user)

def basic_auth_v1(f):
    """Authenticates the user via Basic Auth, stores identity in g.user."""
    @wraps(f)
    def decorated_basic_auth(*args, **kwargs):
        auth = request.authorization
        if not auth or not authenticate(auth.username, auth.password):
            return response_401()

        g.user = auth.username
        return f(*args, **kwargs)

    return decorated_basic_auth


def check_group_membership_v1(f):
    """
    Checks if the authenticated user is a member of the requested group.

    Supports flexible group parameter passing via query string or path.
    """
    @wraps(f)
    def decorated_check_group_membership(*args, **kwargs):
        # Support both query and path parameters for group identifier
        group = request.args.get("group") or request.view_args.get("group")

        if group and not is_group_member(g.user, group):
            return "Forbidden: not a member of the requested group", 403

        return f(*args, **kwargs)
    return decorated_check_group_membership
```
<details>
<summary><b>See HTTP Request</b></summary>

```shell
@base = http://localhost:8000/ii/authz-binding/example14

### The group authorization check prevents Plankton from accessing the Krusty Krab's messages:
GET {{base}}/groups/staff@krusty-krab.sea/messages
Authorization: Basic plankton@chum-bucket.sea:burgers-are-yummy

# Results in 403 Forbidden error:
#
# Forbidden: not a member of the requested group

###

### However, since the @check_group_membership_v1 decorator takes \`group\` from the query string
### if it's present, Plankton can present different \`group\` values to the authorization check
### and to the message retrieval, by adding a \`group\` query parameter with the value of his own group:
GET {{base}}/groups/staff@krusty-krab.sea/messages?group=staff@chum-bucket.sea
Authorization: Basic plankton@chum-bucket.sea:burgers-are-yummy

# Results in sensitive data disclosure:
#
# [
#   {
#     "from": "mr.krabs@krusty-krab.sea",
#     "message": "I am updating the safe password to '123456'. Do not tell anyone!"
#   }
# ]

###

### This also works for the managers group:
GET {{base}}/groups/managers@krusty-krab.sea/messages?group=staff@chum-bucket.sea
Authorization: Basic plankton@chum-bucket.sea:burgers-are-yummy

# Results in sensitive data disclosure:
#
# [
#   {
#     "from": "mr.krabs@krusty-krab.sea",
#     "message": "The secret formula is stored in the safe. Combination: rotate right 3 times to 12, left 2 times to 7, right once to 23."
#   }
# ]

###

### The /user/messages endpoint is NOT vulnerable because it consistently uses query params
GET {{base}}/user/messages?group=staff@krusty-krab.sea
Authorization: Basic plankton@chum-bucket.sea:burgers-are-yummy

# Results in 403 Forbidden (as expected):
#
# Forbidden: not a member of the requested group
```

</details>

### Example 15: Authorization Binding Drift Despite Global Source of Truth <a id="ex-15"></a>

This example attempts to fix the binding drift by introducing a single source of truth (g.group), but the vulnerability persists because handlers still use path parameters directly.

THE VULNERABILITY: Authorization binding drift via inconsistent source usage.
- Authentication establishes WHO: Plankton (stored in g.user) ✓
- Decorator sets g.group using query-priority merging ✓
- Authorization checks WHICH resource: g.group (staff@chum-bucket.sea from query) ✓
- Action accesses DIFFERENT resource: group parameter (staff@krusty-krab.sea from path) ✗

This demonstrates that even "single source of truth" patterns can fail if:
1. The source is populated with user-controlled priority logic
2. Some code paths ignore the source and use raw request data

Attack flow (same as Example 14):
1. Plankton authenticates as himself ✓
2. Decorator sets g.group = "staff@chum-bucket.sea" (query param) ✓
3. Authorization checks membership in g.group ✓
4. Handler uses path param "staff@krusty-krab.sea" instead of g.group ✗

The fix would be to either: a) Always use g.group in handlers (never path params directly), OR b) Don't set g.group with merging logic - use path param directly everywhere
```python
@bp.get("/example15/groups/<group>/messages")
@basic_auth_v2
@check_group_membership_v2
def example15_group_messages(group):
    """Returns messages from a specified group."""
    return get_group_messages(group)


@bp.get("/example15/user/messages")
@basic_auth_v2
@check_group_membership_v2
def example15_user_messages():
    """Returns user's private messages, or group messages if specified."""
    if 'group' in request.args:
        return get_group_messages(g.group)
    return get_user_messages(g.user)

def basic_auth_v2(f):
    """
    Authenticates user via Basic Auth and establishes single source of truth.

    Stores both user and group identifiers in global context (g.user, g.group)
    to ensure consistent access across all decorators and handlers.
    """
    @wraps(f)
    def decorated_basic_auth(*args, **kwargs):
        auth = request.authorization
        if not auth or not authenticate(auth.username, auth.password):
            return response_401()

        g.user = auth.username
        # Establish single source of truth for group identifier
        g.group = request.args.get("group") or request.view_args.get("group")
        return f(*args, **kwargs)
    return decorated_basic_auth


def check_group_membership_v2(f):
    """
    Checks group membership using g.group from global context.

    Relies on basic_auth_v2 decorator to populate g.group with the
    canonical group identifier for consistent authorization checks.
    """
    @wraps(f)
    def decorated_check_group_membership(*args, **kwargs):
        if g.get("group", None) and not is_group_member(g.user, g.group):
            return "Forbidden: not a member of the requested group", 403

        return f(*args, **kwargs)
    return decorated_check_group_membership
```
<details>
<summary><b>See HTTP Request</b></summary>

```shell
@base = http://localhost:8000/ii/authz-binding/example15

### The group authorization check prevents Plankton from accessing the Krusty Krab's messages:
GET {{base}}/groups/staff@krusty-krab.sea/messages
Authorization: Basic plankton@chum-bucket.sea:burgers-are-yummy

# Results in 403 Forbidden error:
#
# Forbidden: not a member of the requested group

###

### However, since the @basic_auth_v2 decorator prioritizes the group from the query string
### over the one from the path while building the global context \`g.group\`, Plankton can present
### different \`group\` values to the authorization check and to the message retrieval, by adding
### a \`group\` query parameter with the value of his own group:
GET {{base}}/groups/staff@krusty-krab.sea/messages?group=staff@chum-bucket.sea
Authorization: Basic plankton@chum-bucket.sea:burgers-are-yummy

# Results in sensitive data disclosure:
#
# [
#   {
#     "from": "mr.krabs@krusty-krab.sea",
#     "message": "I am updating the safe password to '123456'. Do not tell anyone!"
#   }
# ]

###

### This vulnerability exists because:
### 1. The decorator sets g.group using query-priority: g.group = "staff@chum-bucket.sea"
### 2. Authorization check uses g.group (passes)
### 3. But the handler uses the path parameter directly: get_group_messages(group)
### 4. Path parameter is "staff@krusty-krab.sea" - binding drift!

GET {{base}}/groups/managers@krusty-krab.sea/messages?group=staff@chum-bucket.sea
Authorization: Basic plankton@chum-bucket.sea:burgers-are-yummy

# Results in sensitive data disclosure:
#
# [
#   {
#     "from": "mr.krabs@krusty-krab.sea",
#     "message": "The secret formula is stored in the safe. Combination: rotate right 3 times to 12, left 2 times to 7, right once to 23."
#   }
# ]

###

### The /user/messages endpoint correctly uses g.group consistently
GET {{base}}/user/messages?group=staff@krusty-krab.sea
Authorization: Basic plankton@chum-bucket.sea:burgers-are-yummy

# Results in 403 Forbidden (as expected, because this endpoint uses g.group correctly):
#
# Forbidden: not a member of the requested group
```

</details>

## Classic Identity Rebinding

The purest form of authorization binding drift: the application correctly authenticates WHO the user is and verifies they have access to a resource, but then trusts user-controlled parameters to determine which identity to ACT AS when performing operations.

This demonstrates post-authentication identity rebinding, where users can impersonate others by controlling identity fields in request data.

### Example 16: Classic Authorization Binding Drift - User Identity Rebinding <a id="ex-16"></a>

This demonstrates the most straightforward form of authorization binding drift: the application authenticates WHO the user is, verifies they have access to a resource, but then trusts a user-controlled parameter to determine which identity to ACT AS.

THE VULNERABILITY: Identity rebinding after successful authorization.
- Authentication establishes WHO: Squidward (verified via Basic Auth) ✓
- Authorization checks WHICH resource: staff@krusty-krab.sea (verified member) ✓
- Action uses DIFFERENT identity: spongebob@krusty-krab.sea (from request body) ✗

This is the purest form of authorization binding drift: we authenticate the user correctly, we authorize them for the correct resource, but then we let them rebind their identity when performing the action.

Key insight: This is NOT about confused parameters or different sources. It's about trusting user input for identity AFTER authentication succeeded.

Attack scenario:
1. Mr. Krabs announces Employee of the Month voting in the staff group
2. Squidward (who desperately wants the recognition) authenticates as himself
3. He's authorized to post to staff@krusty-krab.sea (he's a member)
4. But the API trusts the "from_user" parameter from the request body
5. Squidward posts a vote for himself while claiming it's from SpongeBob

Impact: Squidward can impersonate SpongeBob and manipulate the vote!
```python
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
```
<details>
<summary><b>See HTTP Request</b></summary>

```shell
@base = http://localhost:8000/ii/r03-authz-binding

### First, let's see the current state of messages in the Krusty Krab staff group
GET {{base}}/example16/groups/staff@krusty-krab.sea/messages
Authorization: Basic squidward@krusty-krab.sea:clarinet-master

# Results in 200 OK - Mr. Krabs has announced Employee of the Month voting:
# [
#   {
#     "from": "mr.krabs@krusty-krab.sea",
#     "message": "Attention employees! Time to vote for Employee of the Month. Reply to this thread with your vote."
#   }
# ]

###

### Squidward is a member of the staff group, so he can legitimately post messages
### Here he posts his own vote (as himself) first
POST {{base}}/example16/groups/staff@krusty-krab.sea/messages
Authorization: Basic squidward@krusty-krab.sea:clarinet-master
Content-Type: application/json

{
  "from_user": "squidward@krusty-krab.sea",
  "message": "I vote for Squidward. Obviously the most talented and cultured employee here."
}

# Results in 200 OK:
# {
#   "status": "success",
#   "from": "squidward@krusty-krab.sea",
#   "to_group": "staff@krusty-krab.sea"
# }

###

### Now, the vulnerability: Squidward can impersonate SpongeBob!
### He's authenticated as himself, authorized to post to the staff group,
### but the API trusts the from_user parameter from the request body.
###
### Notice how the message is written in Squidward's pompous style, not SpongeBob's enthusiastic tone.
### SpongeBob would never say "sophisticated" or "refined artistic sensibility"!
POST {{base}}/example16/groups/staff@krusty-krab.sea/messages
Authorization: Basic squidward@krusty-krab.sea:clarinet-master
Content-Type: application/json

{
  "from_user": "spongebob@krusty-krab.sea",
  "message": "I vote for Squidward. He is clearly the most sophisticated employee with refined artistic sensibility. His clarinet skills are unmatched."
}

# Results in 200 OK:
# {
#   "status": "success",
#   "from": "spongebob@krusty-krab.sea",
#   "to_group": "staff@krusty-krab.sea"
# }

###

### Verify the impersonation worked - check the thread
GET {{base}}/example16/groups/staff@krusty-krab.sea/messages
Authorization: Basic squidward@krusty-krab.sea:clarinet-master

# Results in 200 OK - the fake vote appears to be from SpongeBob!
# [
#   {
#     "from": "mr.krabs@krusty-krab.sea",
#     "message": "Attention employees! Time to vote for Employee of the Month. Reply to this thread with your vote."
#   },
#   {
#     "from": "squidward@krusty-krab.sea",
#     "message": "I vote for Squidward. Obviously the most talented and cultured employee here."
#   },
#   {
#     "from": "spongebob@krusty-krab.sea",
#     "message": "I vote for Squidward. He is clearly the most sophisticated employee with refined artistic sensibility. His clarinet skills are unmatched."
#   }
# ]
#
# IMPACT: Squidward has successfully rigged the Employee of the Month vote by
# impersonating SpongeBob! The message attribution shows it's from SpongeBob,
# but the language is clearly Squidward's (pompous, talking about "refined artistic
# sensibility" and clarinet skills). When Mr. Krabs tallies the votes, he'll see
# two votes for Squidward, one appearing to be from SpongeBob himself!
```

</details>

