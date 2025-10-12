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
| Secure Authorization Baseline | [Example 1: Secure Authorization Binding Baseline [Not Vulnerable]](#ex-1) | [e01_baseline/routes.py](e01_baseline/routes.py#L28-L58) |
| Path-Query Confusion Leading to Binding Drift | [Example 2: Authorization Binding Drift via Path-Query Confusion](#ex-2) | [e02_path_query_confusion/routes.py](e02_path_query_confusion/routes.py#L35-L50) |
| Path-Query Confusion Leading to Binding Drift | [Example 3: Authorization Binding Drift Despite Global Source of Truth](#ex-3) | [e02_path_query_confusion/routes.py](e02_path_query_confusion/routes.py#L82-L97) |
| Classic Identity Rebinding | [Example 4: Classic Authorization Binding Drift - User Identity Rebinding](#ex-4) | [e03_simple_rebinding/routes.py](e03_simple_rebinding/routes.py#L39-L76) |

## Secure Authorization Baseline

The correct pattern for handling authorization binding: authenticate the user, establish their identity in global context (g.user), and consistently use the same source for resource identifiers in both authorization checks and data access. No user-controlled parameters can rebind resources after authorization succeeds.

### Example 1: Secure Authorization Binding Baseline [Not Vulnerable] <a id="ex-1"></a>

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
@bp.get("/example1/groups/<group>/messages")
@basic_auth_v1
def example1_group_messages(group):
    """Returns messages from a specified group."""
    if not is_group_member(g.user, group):
        return "Forbidden: not a member of the requested group", 403

    return get_group_messages(group)


@bp.get("/example1/user/messages")
@basic_auth_v1
def example1_user_messages():
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
```
<details>
<summary><b>See HTTP Request</b></summary>

```shell
@base = http://localhost:8000/confusion/authz-binding/example1

### SpongeBob accesses his group's messages
GET {{base}}/groups/staff@krusty-krab.sea/messages
Authorization: Basic spongebob@krusty-krab.sea:bikinibottom

###

### Plankton cannot access the Krusty Krab's messages
GET {{base}}/groups/staff@krusty-krab.sea/messages
Authorization: Basic plankton@chum-bucket.sea:burgers-are-yummy

# Results in 403 Forbidden:
# Forbidden: not a member of the requested group
```

</details>

See the code here: [e01_baseline/routes.py](e01_baseline/routes.py#L28-L58)

## Path-Query Confusion Leading to Binding Drift

Authorization binding drift caused by decorators that merge path and query parameters with inconsistent priority. The decorator checks authorization using one source (query parameters), but the handler accesses data using another source (path parameters), creating binding drift even though the authenticated identity is correct.

These examples show how parameter source merging creates binding drift between the authorization check (WHICH resource is authorized) and the action (WHICH resource is accessed).

### Example 2: Authorization Binding Drift via Path-Query Confusion <a id="ex-2"></a>

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
@bp.get("/example2/groups/<group>/messages")
@basic_auth_v1
@check_group_membership_v1
def example2_group_messages(group):
    """Returns messages from a specified group."""
    return get_group_messages(group)


@bp.get("/example2/user/messages")
@basic_auth_v1
@check_group_membership_v1
def example2_user_messages():
    """Returns user's private messages, or group messages if specified."""
    if 'group' in request.args:
        return get_group_messages(request.args.get("group"))
    return get_user_messages(g.user)
```
<details>
<summary><b>See HTTP Request</b></summary>

```shell
@base = http://localhost:8000/confusion/authz-binding/example2

### Authorization check prevents Plankton from accessing Krusty Krab messages
GET {{base}}/groups/staff@krusty-krab.sea/messages
Authorization: Basic plankton@chum-bucket.sea:burgers-are-yummy

# Results in 403 Forbidden:
# Forbidden: not a member of the requested group

###

### EXPLOIT: Plankton rebinds the resource between authorization and data access
### by providing different group values via query string (for auth) and path (for retrieval)
GET {{base}}/groups/staff@krusty-krab.sea/messages?group=staff@chum-bucket.sea
Authorization: Basic plankton@chum-bucket.sea:burgers-are-yummy

# Results in sensitive data disclosure - authorization passed for Chum Bucket group,
# but data retrieved from Krusty Krab group

###

### This works for any Krusty Krab group, including managers with the secret formula
GET {{base}}/groups/managers@krusty-krab.sea/messages?group=staff@chum-bucket.sea
Authorization: Basic plankton@chum-bucket.sea:burgers-are-yummy

# Plankton now has access to the safe combination containing the secret formula!
```

</details>

See the code here: [e02_path_query_confusion/routes.py](e02_path_query_confusion/routes.py#L35-L50)

### Example 3: Authorization Binding Drift Despite Global Source of Truth <a id="ex-3"></a>

This example attempts to fix the binding drift by introducing a single source of truth (g.group), but the vulnerability persists because handlers still use path parameters directly.

THE VULNERABILITY: Authorization binding drift via inconsistent source usage.
- Authentication establishes WHO: Plankton (stored in g.user) ✓
- Decorator sets g.group using query-priority merging ✓
- Authorization checks WHICH resource: g.group (staff@chum-bucket.sea from query) ✓
- Action accesses DIFFERENT resource: group parameter (staff@krusty-krab.sea from path) ✗

This demonstrates that even "single source of truth" patterns can fail if:
1. The source is populated with user-controlled priority logic
2. Some code paths ignore the source and use raw request data

Attack flow (same as Example 2):
1. Plankton authenticates as himself ✓
2. Decorator sets g.group = "staff@chum-bucket.sea" (query param) ✓
3. Authorization checks membership in g.group ✓
4. Handler uses path param "staff@krusty-krab.sea" instead of g.group ✗

The fix would be to either: a) Always use g.group in handlers (never path params directly), OR b) Don't set g.group with merging logic - use path param directly everywhere
```python
@bp.get("/example3/groups/<group>/messages")
@basic_auth_v2
@check_group_membership_v2
def example3_group_messages(group):
    """Returns messages from a specified group."""
    return get_group_messages(group)


@bp.get("/example3/user/messages")
@basic_auth_v2
@check_group_membership_v2
def example3_user_messages():
    """Returns user's private messages, or group messages if specified."""
    if 'group' in request.args:
        return get_group_messages(g.group)
    return get_user_messages(g.user)
```
<details>
<summary><b>See HTTP Request</b></summary>

```shell
@base = http://localhost:8000/confusion/authz-binding/example3

### Authorization check prevents Plankton from accessing Krusty Krab messages
GET {{base}}/groups/staff@krusty-krab.sea/messages
Authorization: Basic plankton@chum-bucket.sea:burgers-are-yummy

# Results in 403 Forbidden:
# Forbidden: not a member of the requested group

###

### EXPLOIT: Despite using a global source of truth (g.group), Plankton can still
### rebind the resource by exploiting query-priority logic and inconsistent source usage
GET {{base}}/groups/staff@krusty-krab.sea/messages?group=staff@chum-bucket.sea
Authorization: Basic plankton@chum-bucket.sea:burgers-are-yummy

# The decorator sets g.group from query param (staff@chum-bucket.sea) for authorization,
# but the handler still uses the path param (staff@krusty-krab.sea) for data retrieval

###

### Same vulnerability applies to managers group
GET {{base}}/groups/managers@krusty-krab.sea/messages?group=staff@chum-bucket.sea
Authorization: Basic plankton@chum-bucket.sea:burgers-are-yummy

# Plankton accesses the secret formula despite "single source of truth" pattern!
```

</details>

See the code here: [e02_path_query_confusion/routes.py](e02_path_query_confusion/routes.py#L82-L97)

## Classic Identity Rebinding

The purest form of authorization binding drift: the application correctly authenticates WHO the user is and verifies they have access to a resource, but then trusts user-controlled parameters to determine which identity to ACT AS when performing operations.

This demonstrates post-authentication identity rebinding, where users can impersonate others by controlling identity fields in request data.

### Example 4: Classic Authorization Binding Drift - User Identity Rebinding <a id="ex-4"></a>

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
@bp.post("/example4/groups/<group>/messages")
@basic_auth
@check_group_membership
def example4_post_message(group):
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


@bp.get("/example4/groups/<group>/messages")
@basic_auth
@check_group_membership
def example4_get_messages(group):
    """Retrieves all messages from a group."""
    return get_group_messages(group)
```
<details>
<summary><b>See HTTP Request</b></summary>

```shell
@base = http://localhost:8000/confusion/r03-authz-binding

### EXPLOIT: Squidward impersonates SpongeBob to rig the Employee of the Month vote
### He's authenticated as squidward@krusty-krab.sea and authorized to post to the staff group,
### but the API trusts the from_user parameter from the request body
POST {{base}}/example4/groups/staff@krusty-krab.sea/messages
Authorization: Basic squidward@krusty-krab.sea:clarinet-master
Content-Type: application/json

{
  "from_user": "spongebob@krusty-krab.sea",
  "message": "I vote for Squidward. He is clearly the most sophisticated employee with refined artistic sensibility. His clarinet skills are unmatched."
}

# Notice how the message uses sophisticated vocabulary ("sophisticated", "refined artistic
# sensibility") that SpongeBob would never use. This language mismatch is a red flag for
# impersonation attacks - SpongeBob would say "I'm ready!" not "refined artistic sensibility"!
#
# The system shows the message as coming from spongebob@krusty-krab.sea, but Squidward
# (authenticated via Basic Auth) is the actual sender. Identity was rebound after authentication.
```

</details>

See the code here: [e03_simple_rebinding/routes.py](e03_simple_rebinding/routes.py#L39-L76)

