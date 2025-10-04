# Cross-Component Parsing Drift in Flask

Decorators, middleware, and helpers sometimes grab request data before the view does; if each layer resolves parameters differently, the same call holds two meanings, enabling authentication bypass.

## Overview

Flask's architecture allows each layer (decorators, middleware, before-request hooks, views) to independently choose how to source request data from multiple APIs: `request.args`, `request.form`, `request.values`. When layers use different APIs or apply different merging strategies (e.g., args-priority vs form-priority), the same HTTP request carries multiple semantic interpretations. The authentication check validates one user identity while the handler acts as a different user, enabling authentication bypasses even when all components execute in correct order.

**Key distinction from other inconsistent interpretation bugs:**
- **IS source precedence**: Different components read from different sources (args vs form vs values)
- **IS authentication bypass**: The vulnerability allows acting as a different USER than the one authenticated
- **NOT authorization binding drift**: This is about confused identity during authentication, not about rebinding resources after successful authentication

**The vulnerability pattern:**
1. Decorator/middleware authenticates user credentials from one source (e.g., `request.args`)
2. Handler retrieves identity from different source (e.g., `request.form`)
3. Authentication validates Alice's password, but handler acts as Bob

**Spotting the issue:**
- Audit every decorator or middleware applied to a route and see which request APIs they touch (`request.args` vs `request.form` vs `request.values`).
- Check for custom merging logic that prioritizes sources differently (e.g., `user_from_form or user_from_args`).
- Verify authentication decorators and handlers use the SAME source for user identity.
- Look for decorators that set global state but handlers that read raw request data directly.

**Real-world scenarios:**
- Legacy authentication that reads from query string while new code expects form data
- API refactors that move from GET to POST without updating all middleware
- Shared decorators applied to endpoints with different expected request types

## Table of Contents

| Category | Example | File |
|:---:|:---:|:---:|
| Decorators That Drift | [Example 8: Decorator-based Authentication with Parsing Drift](#ex-8) | [r02_decorator_drift/routes.py](r02_decorator_drift/routes.py#L28-L34) |
| Middleware Short-Circuiting Views | [Example 9: Middleware-based Authentication with Parsing Drift](#ex-9) | [r03_middleware_drift/routes.py](r03_middleware_drift/routes.py#L22-L27) |

## Decorators That Drift

Authentication guards implemented as decorators read user credentials from one source (query parameters), while the view retrieves the user identity from a different source (form data), enabling authentication bypass.

### Example 8: Decorator-based Authentication with Parsing Drift <a id="ex-8"></a>

Shows how using decorators can obscure parameter source confusion, leading to authentication bypass.

Example 8 is functionally equivalent to Example 4 from the source precedence examples, but it may be harder to spot the vulnerability when using decorators because the parameter source logic is split across multiple layers.

THE VULNERABILITY: Authentication bypass via source precedence confusion.
- Authentication decorator validates credentials from request.args (query string)
- Handler retrieves user identity from get_user_ex8(), which prioritizes request.form
- Attack: Provide Alice's credentials in query string, Bob's name in form body
- Result: Authenticate as Alice, but access Bob's messages

This is NOT authorization binding drift - it's authentication bypass because the authenticated identity itself gets confused between authentication check and data access.
```python
@bp.route("/example8", methods=["GET", "POST"])
@authentication_required
def example8():
    messages = get_messages_ex8(get_user_ex8())
    if messages is None:
        return "No messages found", 404
    return messages

def authentication_required(f):
    """
    Authentication decorator that validates user credentials from query parameters.

    VULNERABILITY: This decorator only checks credentials from request.args,
    but the handler may retrieve the user identity from a different source,
    creating an authentication bypass via source precedence confusion.
    """
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

## Middleware Short-Circuiting Views

Before-request hooks authenticate using query parameters only, while views consume form data for the actual operation, creating the same authentication bypass but at the middleware layer.

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

