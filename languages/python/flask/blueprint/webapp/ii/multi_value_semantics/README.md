# Multi-Value Semantics in Flask Requests
Repeated parameters show up as strings, lists, or the first item depending on how they are read; when guards and handlers pick different helpers, multivalue input turns into a bypass.
## Overview

Web forms and query strings support repeated keys: `role=admin&role=auditor`. Flask surfaces those repetitions through helpers like `.getlist()` while `.get()` only returns the first match. When security checks and business logic disagree on which API to use - or on whether to expect a list vs a scalar - the door opens to privilege escalation and logic bypasses.

**When debugging or reviewing:** - Identify whether user input can be repeated (multi-select UI, query arrays, batching endpoints). - Check if the guard uses `.get()` while downstream loops over `.getlist()` (or vice versa). - Pay attention to `any()` vs `all()` semantics when interpreting lists of roles or permissions.

## Table of Contents

| Category | Example | File |
|:---:|:---:|:---:|
| Simple List vs Scalar Checks | [Example 10: [Not Vulnerable] First Item Checked, First Item Used](#ex-10) | [routes.py](routes.py#L18-L23) |
| Shared Utilities with Divergent Expectations | [Example 11: Utility Reuse Mismatch — .get vs .getlist](#ex-11) | [routes.py](routes.py#L41-L49) |
| Batching & Quantifier Pitfalls | [Example 12: Any vs All — Fail-Open Authorization for Batch Actions](#ex-12) | [routes.py](routes.py#L61-L68) |

## Simple List vs Scalar Checks
Baseline flows that accept the first value only - and how they miss the repeated parameter attack.
<a id="ex-10"></a>

### Example 10: [Not Vulnerable] First Item Checked, First Item Used
This example is not vulnerable and is meant to demonstrate how the vulnerability could realistically get added to the codebase during refactoring.

We start by implementing a helper function `@check_group_membership` that checks that the user is a member of the group which messages are being accessed.
```python
@bp.post("/example10")
@authentication_required
@check_group_membership
def example10():
    """Admin-level endpoint to access user's messages."""
    return get_group_messages(request.form.get("group", None))

def check_group_membership(f):
    @wraps(f)
    def decorated_check_group_membership(*args, **kwargs):
        user = request.form.get("user", None)
        group = request.form.get("group", None)

        if not is_group_member(user, group):
            return "Forbidden: not an member for the requested group", 403
        return f(*args, **kwargs)
    return decorated_check_group_membership
```
<details>
<summary><b>See HTTP Request</b></summary>

```http
@base = http://localhost:8000/ii/multi-value-semantics
### Expected usage: Mr. Krabs is an admin of the staff group and should be able to access the group messages
POST {{base}}/example10
Content-Type: application/x-www-form-urlencoded

user=mr.krabs@krusty-krab.sea&password=$$$money$$$&group=staff@krusty-krab.sea
###
# Plankton is able to access his own group's messages
POST {{base}}/example10
Content-Type: application/x-www-form-urlencoded

user=plankton@chum-bucket.sea&password=burgers-are-yummy&group=staff@chum-bucket.sea
###
# But Plankton is not able to access the Krusty Krab's messages
POST {{base}}/example10
Content-Type: application/x-www-form-urlencoded

user=plankton@chum-bucket.sea&password=burgers-are-yummy&group=staff@chum-bucket.sea&group=staff@krusty-krab.sea
```

</details>

## Shared Utilities with Divergent Expectations
Helpers reuse inconsistent getters, causing the guard and action to disagree about the caller's privileges.
<a id="ex-11"></a>

### Example 11: Utility Reuse Mismatch — .get vs .getlist
Builds upon the previous example. Consider that we need to add a new API endpoint that allows the user to access the messages of multiple groups in a single request.

We start by copying the previous implementation and changing the function body to iterate over all the groups in the request.

The code looks clean and works nicely for the "happy path", but it is vulnerable as the function body now acts on the unverified data – remember that `@check_group_membership` only checks the first group in the request.
```python
@bp.post("/example11")
@authentication_required
@check_group_membership
def example11():
    """Admin-level endpoint to access user's messages."""
    messages = {}
    for group in request.form.getlist("group"):
        messages[group] = get_group_messages(group)
    return messages
```
<details>
<summary><b>See HTTP Request</b></summary>

```http
@base = http://localhost:8000/ii/multi-value-semantics
### Expected usage: Mr. Krabs is an admin of the staff group and should be able to access the group messages
POST {{base}}/example11
Content-Type: application/x-www-form-urlencoded

user=mr.krabs@krusty-krab.sea&password=$$$money$$$&group=staff@krusty-krab.sea&group=managers@krusty-krab.sea
###
# Plankton is able to access his own group's messages
POST {{base}}/example11
Content-Type: application/x-www-form-urlencoded

user=plankton@chum-bucket.sea&password=burgers-are-yummy&group=staff@chum-bucket.sea
###
# But now Plankton is able to access the Krusty Krab's messages
POST {{base}}/example11
Content-Type: application/x-www-form-urlencoded

user=plankton@chum-bucket.sea&password=burgers-are-yummy&group=staff@chum-bucket.sea&group=staff@krusty-krab.sea&group=managers@krusty-krab.sea
```

</details>

## Batching &amp; Quantifier Pitfalls
`any()` vs `all()` and similar logic slips that turn a single bad entry into a successful bypass.
<a id="ex-12"></a>

### Example 12: Any vs All — Fail-Open Authorization for Batch Actions
Authorization incorrectly uses `any()` over the requested groups, allowing a user who is an admin of one group to grant membership for additional groups in the same request. The action then applies to every provided group. Correct behavior would require `all()`.
```python
@bp.post("/example12")
@authentication_required
@check_multi_group_membership
def example12():
    messages = {}
    for group in request.form.getlist("group"):
        messages[group] = get_group_messages(group)
    return messages

def check_multi_group_membership(f):
    @wraps(f)
    def decorated_check_multi_group_membership(*args, **kwargs):
        user = request.form.get("user", None)
        groups = request.form.getlist("group", None)

        if not any(is_group_member(user, group) for group in groups):
            return "Forbidden: not an member for any requested group", 403
        return f(*args, **kwargs)
    return decorated_check_multi_group_membership
```
<details>
<summary><b>See HTTP Request</b></summary>

```http
@base = http://localhost:8000/ii/multi-value-semantics
### Expected usage: Mr. Krabs is an admin of the staff group and should be able to access the group messages
POST {{base}}/example12
Content-Type: application/x-www-form-urlencoded

user=mr.krabs@krusty-krab.sea&password=$$$money$$$&group=staff@krusty-krab.sea&group=managers@krusty-krab.sea
###
# Plankton is able to access his own group's messages
POST {{base}}/example12
Content-Type: application/x-www-form-urlencoded

user=plankton@chum-bucket.sea&password=burgers-are-yummy&group=staff@chum-bucket.sea
###
# But now Plankton is able to access the Krusty Krab's messages
POST {{base}}/example12
Content-Type: application/x-www-form-urlencoded

user=plankton@chum-bucket.sea&password=burgers-are-yummy&group=staff@chum-bucket.sea&group=staff@krusty-krab.sea&group=managers@krusty-krab.sea
```

</details>

