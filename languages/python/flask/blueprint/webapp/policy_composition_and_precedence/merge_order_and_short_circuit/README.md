# Merge Order and Short-Circuit Pitfalls

Layering a permissive guard ahead of a stricter policy, or returning early from a cache, means the stronger rule does not execute.

## Overview

Security controls in Flask—decorators, blueprints, before_request hooks—execute in a specific order. When a permissive check runs before a stricter policy, or when middleware returns early before handler-level guards execute, the stronger protection never runs. Flask applies decorators bottom-up (the outermost decorator runs first), so a guard decorator placed above an auth decorator will execute before authentication state is prepared. Even when all components agree on data sources, incorrect execution sequencing creates authorization bypasses. This is distinct from parsing drift: the vulnerability exists purely in the temporal ordering of security checks, not in how they interpret request data.

**Practice tips:**
- Audit decorator order whenever mixing auth, caching, and convenience helpers. Remember: outer decorators run FIRST in Flask.
- Ensure guards don't depend on state (`g.*`) that inner decorators haven't set yet.
- Ensure middleware that returns responses still enforces critical checks.
- Write regression tests that show the stricter guard running in the expected order and seeing prepared state.
- When debugging bypasses, check BOTH execution order AND data sourcing—vulnerabilities often involve both dimensions.

## Table of Contents

| Category | Example | File |
|:---:|:---:|:---:|
| Decorator Execution Order Bypasses | [Example 16: Authorization Bypass via Decorator Execution Order](#ex-16) | [routes.py](routes.py#L25-L30) |

## Decorator Execution Order Bypasses

Guards that run before authentication or state preparation become no-ops, allowing unauthorized access.

### Example 16: Authorization Bypass via Decorator Execution Order <a id="ex-16"></a>

We try to fix the root cause of the vulnerability here by enforcing correct merging order – view args take precedence over query args. Additionally, we enforce that only one of the two can be present.

The code, however, remains vulnerable despite these efforts! This time, the problem is that the `@check_group_membership_v2` decorator is applied too early – before the `@basic_auth_v3` decorator which is responsible for setting the `g.group` global variable. This makes `@check_group_membership_v2` a no-op.

This is a pure policy composition issue: the guard decorator executes before the authentication decorator prepares the state it depends on. Flask applies decorators bottom-up (outer decorator runs first), so @check_group_membership_v2 sees g.group = None and passes all requests.
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
@base = http://localhost:8000/policy-composition-and-precedence/merge-order-and-short-circuit/example16

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

