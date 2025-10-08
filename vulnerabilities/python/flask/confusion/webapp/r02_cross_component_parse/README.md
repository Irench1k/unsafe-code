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
3. Authentication validates SpongeBob's password, but handler acts as Squidward

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
| Secure Baseline | [Example 1: Consistent Parameter Sourcing [Not Vulnerable]](#ex-1) | [e01_baseline/routes.py](e01_baseline/routes.py#L28-L41) |
| Decorator Drift | [Example 2: Decorator-based Authentication with Parsing Drift](#ex-2) | [e02_decorator_drift/routes.py](e02_decorator_drift/routes.py#L28-L34) |
| Middleware Drift | [Example 3: Middleware-based Authentication with Parsing Drift](#ex-3) | [e03_middleware_drift/routes.py](e03_middleware_drift/routes.py#L22-L27) |

## Secure Baseline

The correct pattern for handling authentication across decorator and handler layers: consistently use the same parameter source (request.args) in both the authentication decorator and the handler. This prevents confusion about which user identity is being validated versus acted upon.

### Example 1: Consistent Parameter Sourcing [Not Vulnerable] <a id="ex-1"></a>

This baseline demonstrates the secure pattern for handling authentication when decorators and handlers need to access the same user identity.

THE SECURE PATTERN: Consistent parameter sourcing across all layers.
- Authentication decorator validates credentials from request.args
- Handler retrieves user identity from the SAME source (request.args)
- Both layers use identical logic: request.args.get("user")
- Result: Authentication and data access work on the same identity

This prevents authentication bypass by ensuring that the identity validated during authentication is the exact same identity used for data access. There is no confusion between different request data sources.

Compare this to the vulnerable examples that follow, where different layers source the user identity from different request properties, creating authentication bypass vulnerabilities.
```python
@bp.route("/example1", methods=["GET", "POST"])
@authentication_required
def example1():
    """
    Returns user's messages after authentication.

    Securely retrieves user identity from the same source used for
    authentication (query parameters), preventing any confusion.
    """
    user = request.args.get("user")
    messages = get_messages(user)
    if messages is None:
        return "No messages found", 404
    return messages

def authentication_required(f):
    """
    Authenticates the user via query parameters.

    This decorator consistently sources both username and password from
    request.args, matching the source used by the handler.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = request.args.get("user")
        password = request.args.get("password")

        if not authenticate(user, password):
            return "Authentication required", 401

        return f(*args, **kwargs)

    return decorated_function
```
<details>
<summary><b>See HTTP Request</b></summary>

```shell
@base = http://localhost:8000/confusion/cross-component-parse

### Secure Baseline: SpongeBob authenticates and retrieves his own messages
GET {{base}}/example1?user=spongebob&password=bikinibottom
#
# {
#   "owner": "spongebob",
#   "messages": [
#     {
#       "from": "patrick",
#       "message": "Hey SpongeBob, wanna go jellyfishing?"
#     }
#   ]
# }
#
# This example is SECURE. Both authentication and data retrieval use
# consistent parameter sources (request.args), preventing bypass attempts.
```

</details>

## Decorator Drift

Authentication guards implemented as decorators read user credentials from one source (query parameters), while the view retrieves the user identity from a different source (form data), enabling authentication bypass.

### Example 2: Decorator-based Authentication with Parsing Drift <a id="ex-2"></a>

Shows how using decorators can obscure parameter source confusion, leading to authentication bypass.

Example 2 is functionally equivalent to Example 4 from the source precedence examples, but it may be harder to spot the vulnerability when using decorators because the parameter source logic is split across multiple layers.

THE VULNERABILITY: Authentication bypass via source precedence confusion.
- Authentication decorator validates credentials from request.args (query string)
- Handler retrieves user identity from get_user_ex2(), which prioritizes request.form
- Attack: Provide SpongeBob's credentials in query string, Squidward's name in form body
- Result: Authenticate as SpongeBob, but access Squidward's messages

This is NOT authorization binding drift - it's authentication bypass because the authenticated identity itself gets confused between authentication check and data access.
```python
@bp.route("/example2", methods=["GET", "POST"])
@authentication_required
def example2():
    messages = get_messages_ex2(get_user_ex2())
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
    def decorated_example2(*args, **kwargs):
        if not authenticate_ex2():
            return "Invalid user or password", 401
        return f(*args, **kwargs)

    return decorated_example2
```
<details>
<summary><b>See HTTP Request</b></summary>

```shell
@base = http://localhost:8000/confusion/cross-component-parse

### Expected Usage: SpongeBob retrieves his own messages
GET {{base}}/example2?user=spongebob&password=bikinibottom
#
# {
#   "owner": "spongebob",
#   "messages": [
#     {
#       "from": "patrick",
#       "message": "Hey SpongeBob, wanna go jellyfishing?"
#     }
#   ]
# }

###

### EXPLOIT: Authenticate as SpongeBob but retrieve Mr. Krabs's messages
### Decorator checks query params (user=spongebob), handler reads form data (user=mr.krabs)
GET {{base}}/example2?user=spongebob&password=bikinibottom
Content-Type: application/x-www-form-urlencoded

user=mr.krabs
#
# {
#   "owner": "mr.krabs",
#   "messages": [
#     {
#       "from": "pearl",
#       "message": "Daddy, I need $500 for the school dance! It's an EMERGENCY!"
#     },
#     {
#       "from": "mr.krabs",
#       "message": "Note to self: moved the secret formula to the auxiliary vault. Combination is me phone number backwards: 5665-321."
#     }
#   ]
# }
#
# IMPACT: Plankton discovers the auxiliary vault location and combination,
# gaining direct access to the Krabby Patty secret formula! Cross-component
# parameter sourcing allows authenticating as one user while accessing another's data.
```

</details>

## Middleware Drift

Before-request hooks authenticate using query parameters only, while views consume form data for the actual operation, creating the same authentication bypass but at the middleware layer.

### Example 3: Middleware-based Authentication with Parsing Drift <a id="ex-3"></a>

Demonstrates how Flask's middleware system can contribute to parameter source confusion.

Example 3 is functionally equivalent to Example 4 from the old parameter source confusion examples, but it may be harder to spot the vulnerability while using middleware.

The before_request middleware authenticates using request.args.get("user"), but the handler retrieves the user via get_user(request) which prioritizes request.form over request.args. This allows an attacker to authenticate as SpongeBob but access Squidward's messages.
```python
@bp.route("/example3", methods=["GET", "POST"])
def example3():
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
@base = http://localhost:8000/confusion/cross-component-parse

### Expected Usage: SpongeBob retrieves his own messages
GET {{base}}/example3?user=spongebob&password=bikinibottom
#
# {
#   "owner": "spongebob",
#   "messages": [
#     {
#       "from": "patrick",
#       "message": "Hey SpongeBob, wanna go jellyfishing?"
#     }
#   ]
# }

###

### EXPLOIT: Authenticate as SpongeBob but retrieve Squidward's messages
### Middleware checks query params (user=spongebob), handler reads form data (user=squidward)
GET {{base}}/example3?user=spongebob&password=bikinibottom
Content-Type: application/x-www-form-urlencoded

user=squidward
#
# {
#   "owner": "squidward",
#   "messages": [
#     {
#       "from": "squidward",
#       "message": "Dear diary, Mr. Krabs keeps the register key taped under his desk. The morning shift code is 1-9-6-2."
#     },
#     {
#       "from": "art.dealer",
#       "message": "Your painting 'Bold and Brash' has been rejected from the Tentacles Art Gallery. Again."
#     }
#   ]
# }
#
# IMPACT: Plankton learns how to access the cash register and discovers
# Squidward's vulnerable emotional state, making him a prime social engineering
# target. Middleware-handler parameter inconsistency is especially dangerous
# because security and business logic execute in separate architectural layers.
```

</details>

