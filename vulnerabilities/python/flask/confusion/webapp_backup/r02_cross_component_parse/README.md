# Cross-Component Parsing Confusion in Flask

When middleware, decorators, and handlers parse user identity from different sources or with different precedence, authentication validates one user while business logic acts on another.

## Overview

Flask applications naturally evolve from verbose inline authentication to sophisticated middleware and decorator patterns. Each refactoring step seems to improve code clarity and reduce duplication, but subtle inconsistencies at component boundaries create exploitable vulnerabilities.

This section demonstrates how **cross-component parsing confusion** emerges through realistic refactoring scenarios, where each component (middleware, decorator, handler) makes independent decisions about where to read user identity.

**Key distinction from source precedence (r01):**
- **r01**: Authentication and handler both in one place, but read from different sources
- **r02**: Authentication and handler **separated** into middleware/decorator/handler layers
- **Attack surface**: Confusion happens at component boundaries, harder to spot in code review

**The vulnerability pattern:**
1. Middleware extracts principal from one source and stores in `g.user`
2. Decorator validates credentials from another source
3. Handler uses `g.user` OR reads directly from yet another source
4. Attacker exploits mismatches to authenticate as themselves but act on victim's data

**Why developers create this pattern:**
- Progressive refactoring seems to improve code quality
- Each component looks reasonable in isolation
- Testing focuses on happy path (single username in request)
- Code review examines components separately, misses interactions

**Spotting the issue:**
- Trace how user identity flows: middleware → g → decorator → handler
- Check if middleware/decorator/handler all use same source (form vs args vs values)
- Verify precedence rules match when checking multiple sources
- Test with username in multiple locations (query, form, headers)
- Look for handlers that bypass g.user and read directly from request

## Table of Contents

| Category | Example | File |
|:---:|:---:|:---:|
| Baseline - Verbose Inline Authentication | [Example 1: Secure Baseline with Verbose Inline Authentication](#ex-1) | [e01_baseline/routes.py](e01_baseline/routes.py#L33-L57) |
| Middleware Introduction | [Example 2: Middleware with Source Precedence Bug](#ex-2) | [e02_middleware/routes.py](e02_middleware/routes.py#L60-L72) |
| Decorator with request.values | [Example 3: Decorator with `request.values` Confusion](#ex-3) | [e03_decorator/routes.py](e03_decorator/routes.py#L30-L43) |
| Fixed Decorator, Broken Handler | [Example 4: Decorator with Incomplete Fix](#ex-4) | [e04_decorator_2/routes.py](e04_decorator_2/routes.py#L27-L40) |
| Error Handler Patterns | [Example 5: Basic Authentication with Query Parameter Bug](#ex-5) | [e05_basic_auth/routes.py](e05_basic_auth/routes.py#L91-L112) |
| Basic Authentication Migration | [Example 6: Error Handler with Fail-Open Vulnerability](#ex-6) | [e06_error_handler/routes.py](e06_error_handler/routes.py#L99-L109) |

## Baseline - Verbose Inline Authentication

Secure but repetitive authentication patterns that create pressure for refactoring. Every endpoint has 4-6 lines of identical authentication boilerplate:

1. Extract user and password from request.form
2. Call authenticate(user, password)
3. Return 401 if authentication fails
4. Proceed with business logic

This repetition makes code harder to maintain, increases copy-paste errors, and obscures business logic. Subsequent examples show various refactoring approaches and the subtle security issues they introduce.

### Example 1: Secure Baseline with Verbose Inline Authentication <a id="ex-1"></a>

Demonstrates secure but repetitive authentication. Every endpoint validates credentials inline with 4 lines of identical logic before executing business operations. This verbose pattern creates pressure to refactor into middleware or decorators, as shown in subsequent examples.

Check out the full routes.py file to see all four endpoints defined there and how much code is duplicated here. Pay attention to lack of standardization – even the user identity gets extracted in multiple ways:

- request.form.get("user")
- request.form.get("sender")
- request.view_args("username")

There are no vulnerabilities here, and the code is relatively straightforward to review, but the large amount of repetition and inconsistencies make it hard to maintain, which typically gets addressed by refactoring into middleware or decorators.
```python
@bp.post("/messages/list")
def list_messages():
    """Lists all messages for the authenticated user."""
    try:
        # Inline authentication (repeated in all endpoints)
        user = request.form.get("user")
        password = request.form.get("password")

        if not authenticate(user, password):
            # Note that although Flask will automatically convert *some*
            # data types to JSON like dictionaries, there are some other
            # data types that don't get converted automatically, so it's
            # best to always use jsonify() to ensure the response is a
            # valid JSON with proper headers set.
            return jsonify({"error": "Invalid credentials"}), 401

        # Business logic
        messages = get_messages(user)
        return jsonify({"user": user, "messages": messages}), 200
    except KeyError:
        return jsonify({"error": "Resource not found"}), 404
    except Exception:
        # We need to catch any unhandled exceptions and map them to
        # a safe error messages to avoid leaking sensitive information
        return jsonify({"error": "Failed to retrieve messages"}), 500
```
<details>
<summary><b>See HTTP Request</b></summary>

```shell
@base = http://localhost:8000/confusion/cross-component-parse/example1

### SpongeBob lists his messages
POST {{base}}/messages/list
Content-Type: application/x-www-form-urlencoded

user=spongebob&password=bikinibottom

# {
#   "messages": [
#     {
#       "from": "patrick",
#       "id": 1,
#       "read": false,
#       "text": "SpongeBob! I'm ready! I'm ready! Let's go jellyfishing!"
#     },
#     ...
#   ],
#   "user": "spongebob"
# }

### Squidward sends a message to SpongeBob
POST {{base}}/messages/new
Content-Type: application/x-www-form-urlencoded

sender=squidward&password=clarinet123
&recipient=spongebob&text=Hello, SpongeBob!

# {
#   "message_id": 5,
#   "recipient": "spongebob",
#   "sender": "squidward"
# }

### Squidward views SpongeBob's profile
POST {{base}}/profile/spongebob/view
Content-Type: application/x-www-form-urlencoded

user=squidward&password=clarinet123&profile_owner=spongebob

# {
#   "bio": "I'm ready! Fry cook at the Krusty Krab.",
#   "display_name": "SpongeBob SquarePants",
#   "username": "spongebob"
# }

### Squidward edits his own profile
PATCH {{base}}/profile/squidward/edit
Content-Type: application/x-www-form-urlencoded

user=squidward&password=clarinet123&display_name=Squ1dward&bio=You wouldn't understand anyway.

# {
#   "status": "updated",
#   "user": "squidward"
# }

### Squidward attempts to edit SpongeBob's profile
PATCH {{base}}/profile/spongebob/edit
Content-Type: application/x-www-form-urlencoded

user=squidward&password=clarinet123&display_name=Spongebob sucks&bio=Spongebob is a sucky sponge.

# {
#   "error": "Invalid credentials"
# }
```

</details>

See the code here: [e01_baseline/routes.py](e01_baseline/routes.py#L33-L57)

## Middleware Introduction

Introduces Flask blueprint middleware to consolidate authentication into g.user. Explains Flask request lifecycle and g object. Contains source precedence bug where one handler reads from wrong source (request.args instead of request.form).

### Example 2: Middleware with Source Precedence Bug <a id="ex-2"></a>

This example introduces Flask blueprint middleware to reduce authentication boilerplate. The @bp.before_request decorator runs before every endpoint, validates credentials, and stores the authenticated user in g.user.

Note that due to lack of standardization, in the e01_baseline we accessed user identity in multiple ways. As we replace the inline authentication with middleware, we standardize on a single way to access the user identity.

While refactoring, developers need to remove previous authentication logic and replace the user identity with g.user. However, the `/profile/<username>/view` endpoint accepted two usernames - one for authentication (`request.form`) and one for viewing the profile (`request.view_args`). This endpoint was refactored correctly - by just removing the authentication and keeping the `<username>` for profile access. But then the same method was used to refactor the sibling endpoint `/profile/<username>/edit` - introducing a source precedence vulnerability.

An attacker authenticates with their credentials in the form body, then specifies a victim's username in the path to edit their profile.
```python
@bp.post("/messages/list")
def list_messages():
    """Lists all messages for the authenticated user."""
    try:
        # Business logic
        messages = get_messages(g.user)
        return jsonify({"user": g.user, "messages": messages}), 200
    except KeyError:
        return jsonify({"error": "Resource not found"}), 404
    except Exception:
        # We need to catch any unhandled exceptions and map them to
        # a safe error messages to avoid leaking sensitive information
        return jsonify({"error": "Failed to retrieve messages"}), 500

@bp.patch("/profile/<username>/edit")
def edit_profile(username):
    """Edits the authenticated user's profile."""
    try:
        display_name = request.form.get("display_name")
        bio = request.form.get("bio")

        if not display_name and not bio:
            return jsonify({"error": "No updates provided"}), 400

        success = update_profile(username, display_name, bio)
        if not success:
            return jsonify({"error": "Update failed"}), 500

        return jsonify({"status": "updated", "user": username}), 200
    except KeyError:
        return jsonify({"error": "Resource not found"}), 404
    except ValueError:
        return jsonify({"error": "Invalid input provided"}), 400
    except Exception:
        return jsonify({"error": "Failed to update profile"}), 500

@bp.before_request
def authenticate_user():
    """
    Blueprint-level middleware that runs before every request.

    Validates credentials from form body and stores authenticated user in Flask's g
    object (request-scoped global storage).
    """
    user = request.form.get("user")
    password = request.form.get("password")

    if not authenticate(user, password):
        return jsonify({"error": "Invalid credentials"}), 401

    # Store authenticated user for handlers to use
    g.user = user
```
<details>
<summary><b>See HTTP Request</b></summary>

```shell
@base = http://localhost:8000/confusion/cross-component-parse/example2

### Squidward views his own profile
POST {{base}}/profile/squidward/view
Content-Type: application/x-www-form-urlencoded

user=squidward&password=clarinet123

# {
#   "bio": "Clarinet enthusiast and cashier.",
#   "display_name": "Squidward Tentacles",
#   "username": "squidward"
# }

### Squidward views SpongeBob's profile
POST {{base}}/profile/spongebob/view
Content-Type: application/x-www-form-urlencoded

user=squidward&password=clarinet123

# {
#   "bio": "I'm ready! Fry cook at the Krusty Krab.",
#   "display_name": "SpongeBob SquarePants",
#   "username": "spongebob"
# }

### Squidward edits his own profile
PATCH {{base}}/profile/squidward/edit
Content-Type: application/x-www-form-urlencoded

user=squidward&password=clarinet123&display_name=Squ1dward&bio=You wouldn't understand anyway.

# {
#   "status": "updated",
#   "user": "squidward"
# }

### Squidward notices that in the previous request his username appeared twice, and tries to edit SpongeBob's profile!
PATCH {{base}}/profile/spongebob/edit
Content-Type: application/x-www-form-urlencoded

user=squidward&password=clarinet123&display_name=Spongebob sucks&bio=Spongebob is a sucky sponge.

# {
#   "status": "updated",
#   "user": "spongebob"
# }

### SpongeBob's profile has been updated by Squidward!
POST {{base}}/profile/spongebob/view
Content-Type: application/x-www-form-urlencoded

user=squidward&password=clarinet123

# {
#   "bio": "Spongebob is a sucky sponge.",
#   "display_name": "Spongebob sucks",
#   "username": "spongebob"
# }
```

</details>

See the code here: [e02_middleware/routes.py](e02_middleware/routes.py#L60-L72)

## Decorator with request.values

Adds authentication decorator using request.values for "flexibility", creating precedence confusion similar to r01's examples. Middleware sets g.user from request.form while decorator validates from request.values (args take precedence).

### Example 3: Decorator with `request.values` Confusion <a id="ex-3"></a>

Middleware executes on each request within app / blueprint. Real-world apps often need different authentication methods, such as having some endpoints unauthenticated or having some endpoints authenticated with API keys / service-to-service authn.

In this example, we move authentication logic to a decorator `@require_auth` - it only applies to functions that are explicitly marked with it.

Decorator uses `request.values` during authentication, which merges user input from query string and form body. However, in the `/messages/new` endpoint, the `create_message()` function is provided with the sender identity that comes explicitly from `request.form` method. Thus, attacker can **impersonate other users** by providing attacker's username in the query string, but victim's username and attacker's password in the form body.
```python
@bp.post("/messages/list")
@require_auth
def list_messages():
    """Lists all messages for the authenticated user."""
    try:
        # Business logic
        messages = get_messages(request.values.get("user"))
        return jsonify({"user": g.user, "messages": messages}), 200
    except KeyError:
        return jsonify({"error": "Resource not found"}), 404
    except Exception:
        # We need to catch any unhandled exceptions and map them to
        # a safe error messages to avoid leaking sensitive information
        return jsonify({"error": "Failed to retrieve messages"}), 500

def require_auth(f):
    """Authentication decorator."""

    @wraps(f)
    def decorated(*args, **kwargs):
        user = request.values.get("user")
        password = request.values.get("password")

        if not authenticate(user, password):
            return jsonify({"error": "Invalid credentials"}), 401

        # Store authenticated user in g
        g.user = user

        return f(*args, **kwargs)

    return decorated
```
<details>
<summary><b>See HTTP Request</b></summary>

```shell
@base = http://localhost:8000/confusion/cross-component-parse/example3

### SpongeBob lists his messages
POST {{base}}/messages/list
Content-Type: application/x-www-form-urlencoded

user=spongebob&password=bikinibottom

# {
#   "messages": [
#     {
#       "from": "patrick",
#       "id": 1,
#       "read": false,
#       "text": "SpongeBob! I'm ready! I'm ready! Let's go jellyfishing!"
#     }
#   ],
#   "user": "spongebob"
# }

### Plankton tries to recruit SpongeBob and sends him a job offer
POST {{base}}/messages/new
Content-Type: application/x-www-form-urlencoded

user=plankton&password=chumbucket&recipient=spongebob&text=SpongeBob, come work for me!

# {
#   "message_id": 5,
#   "recipient": "spongebob",
#   "sender": "plankton"
# }

### Plankton impersonates Mr. Krabs and sends a message "firing" SpongeBob
POST {{base}}/messages/new?user=plankton
Content-Type: application/x-www-form-urlencoded

user=mr.krabs&password=chumbucket&recipient=spongebob&text=You're fired!

# {
#   "message_id": 6,
#   "recipient": "spongebob",
#   "sender": "mr.krabs"
# }

### SpongeBob lists his messages and sees a message from Mr. Krabs that was sent by Plankton
POST {{base}}/messages/list
Content-Type: application/x-www-form-urlencoded

user=spongebob&password=bikinibottom

# {
#   "messages": [
#     {
#       "from": "patrick",
#       "id": 1,
#       "read": false,
#       "text": "SpongeBob! I'm ready! I'm ready! Let's go jellyfishing!"
#     },
#     {
#       "from": "plankton",
#       "id": 5,
#       "read": false,
#       "text": "SpongeBob, come work for me!"
#     },
#     {
#       "from": "mr.krabs",
#       "id": 6,
#       "read": false,
#       "text": "You're fired!"
#     }
#   ],
#   "user": "spongebob"
# }
```

</details>

See the code here: [e03_decorator/routes.py](e03_decorator/routes.py#L30-L43)

## Fixed Decorator, Broken Handler

Decorator is "fixed" to reuse g.user from middleware (secure!), but a new handler copies the old decorator's buggy logic inline. Demonstrates how copy-paste programming reintroduces fixed vulnerabilities.

### Example 4: Decorator with Incomplete Fix <a id="ex-4"></a>

In this example we attempted to fix the vulnerability by replacing the `request.values` method in the decorator with the `request.form` method.

When we test the previous vulnerability, we see that now it is fixed, which is good news.

However, the fix inadvertently introduced a new vulnerability because the existing code in the `/message/list` endpoint accesses the `user` from the combined dictionary `request.values`. The attacker can now view victim's messages by sending attacker's credentials via the body form (used in `@require_auth`), and the victim's username via the query string (used to access the messages).
```python
@bp.post("/messages/list")
@require_auth
def list_messages():
    """Lists all messages for the authenticated user."""
    try:
        # Business logic
        messages = get_messages(request.values.get("user"))
        return jsonify({"user": g.user, "messages": messages}), 200
    except KeyError:
        return jsonify({"error": "Resource not found"}), 404
    except Exception:
        # We need to catch any unhandled exceptions and map them to
        # a safe error messages to avoid leaking sensitive information
        return jsonify({"error": "Failed to retrieve messages"}), 500

def require_auth(f):
    """Authentication decorator."""

    @wraps(f)
    def decorated(*args, **kwargs):
        # Security Fix! Don't use \`request.values\` here please, it is insecure.
        user = request.form.get("user")
        password = request.form.get("password")

        if not authenticate(user, password):
            return jsonify({"error": "Invalid credentials"}), 401

        # Store authenticated user in g
        g.user = user

        return f(*args, **kwargs)

    return decorated
```
<details>
<summary><b>See HTTP Request</b></summary>

```shell
@base = http://localhost:8000/confusion/cross-component-parse/example4

### Developers re-test the unauthorized access vulnerability from example 3, and confirm that it's fixed
POST {{base}}/messages/new?user=plankton
Content-Type: application/x-www-form-urlencoded

user=mr.krabs&password=chumbucket&recipient=spongebob&text=You're fired!

# {
#   "error": "Invalid credentials"
# }

### However, the fix introduced a new vulnerability in another endpoint, and now Plankton can read SpongeBob's messages instead!
POST {{base}}/messages/list?user=spongebob
Content-Type: application/x-www-form-urlencoded

user=plankton&password=chumbucket

# {
#   "messages": [
#     {
#       "from": "patrick",
#       "id": 1,
#       "read": false,
#       "text": "SpongeBob! I'm ready! I'm ready! Let's go jellyfishing!"
#     }
#   ],
#   "user": "plankton"
# }
```

</details>

See the code here: [e04_decorator_2/routes.py](e04_decorator_2/routes.py#L27-L40)

## Error Handler Patterns

Introduces errorhandler with fail-open vulnerability. Known exceptions map to safe messages, but unexpected exceptions expose full details including passwords. Demonstrates information disclosure through defensive-looking error handling.

### Example 5: Basic Authentication with Query Parameter Bug <a id="ex-5"></a>

Modernized authentication using HTTP Basic Auth via Authorization header. User identity is now extracted into `g.user` from this header.

Now the clients won't be sending credentials via the form parameters (HTTP request body) anymore. It means:

1. We are free to use GET method.
2. We remove a footgun by enforcing a single source of truth for identity.
Credentials are not mixed with other user input anymore, making it *almost* impossible to introduce source confusion bugs.

Despite this, the endpoint `/profile/<username>/edit` is vulnerable because the profile it modifies comes from the path argument without verifying that it matches the authenticated user. The vulnerability is hard to spot because it lies deep inside the call stack. `get_profile` is built for convenience: it is used both when we edit the profile and when we view the profile of other users.
```python
@bp.patch("/profile/<username>/edit")
@require_auth
def edit_profile(username):
    """Edits the authenticated user's profile."""
    try:
        display_name = request.form.get("display_name")
        bio = request.form.get("bio")

        if not display_name and not bio:
            return jsonify({"error": "No updates provided"}), 400

        success = update_profile(display_name, bio)
        if not success:
            return jsonify({"error": "Update failed"}), 500

        return jsonify({"status": "updated", "user": g.user}), 200
    except KeyError:
        return jsonify({"error": "Resource not found"}), 404
    except ValueError:
        return jsonify({"error": "Invalid input provided"}), 400
    except Exception:
        return jsonify({"error": "Failed to update profile"}), 500

def require_auth(f):
    """
    Authentication decorator using HTTP Basic Authentication.

    Extracts credentials from Authorization header, validates them, and stores
    authenticated user in g.user for handler use.
    """

    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth:
            return {"error": "Authentication required"}, 401

        if not authenticate(auth.username, auth.password):
            return {"error": "Invalid credentials"}, 401

        # Store authenticated user in g
        g.user = auth.username

        return f(*args, **kwargs)

    return decorated

def get_profile(internal=False):
    """Gets a user's profile."""
    from flask import g, request

    # This is meant for /profile/<username>/ endpoints which are explicitly meant
    # for accessing other users' profiles - so we prioritize view_args over g.user here
    user = sanitize_username(request.view_args.get("username") or g.user)

    raw_profile = db["profiles"].get(user)
    if internal or raw_profile is None:
        return raw_profile

    profile = raw_profile.copy()
    profile["username"] = user
    return profile


def update_profile(display_name=None, bio=None):
    """Updates a user's profile."""
    profile = get_profile(internal=True)

    if display_name:
        profile["display_name"] = display_name
    if bio:
        profile["bio"] = bio

    return True
```
<details>
<summary><b>See HTTP Request</b></summary>

```shell
@base = http://localhost:8000/confusion/cross-component-parse/example5

### Squidward views SpongeBob's profile
GET {{base}}/profile/spongebob/view
Authorization: Basic squidward:clarinet123

# {
#   "bio": "I'm ready! Fry cook at the Krusty Krab.",
#   "display_name": "SpongeBob SquarePants",
#   "username": "spongebob"
# }

### Squidward edits SpongeBob's profile
PATCH {{base}}/profile/spongebob/edit
Authorization: Basic squidward:clarinet123
Content-Type: application/x-www-form-urlencoded

display_name=Spongebob sucks&bio=Spongebob is a sucky sponge.

# {
#   "status": "updated",
#   "user": "squidward"
# }

### The SpongeBob's profile is updated
GET {{base}}/profile/spongebob/view
Authorization: Basic squidward:clarinet123

# {
#   "bio": "Spongebob is a sucky sponge.",
#   "display_name": "Spongebob sucks",
#   "username": "spongebob"
# }
```

</details>

See the code here: [e05_basic_auth/routes.py](e05_basic_auth/routes.py#L91-L112)

## Basic Authentication Migration

Modernizes to HTTP Basic Auth via Authorization header. Most endpoints correctly use g.user, but one handler reads username from query string instead, enabling authenticated users to view any profile.

### Example 6: Error Handler with Fail-Open Vulnerability <a id="ex-6"></a>

In this example we showcase two important Flask features: error handler and `after_request` middleware. They allow us to remove large amount of code duplication. Compare routes.py in this example with the previous example e05.

The weakness lies withing the `handle_error` function which is meant to sanitize error messages to prevent leaking sensitive data. However, when the `error_type` does not correspond to any of the keys in the `ERROR_MESSAGES` dictionary, the handler fails open and leaks the full exception.

What goes wrong:
1. The `profile_is_active` function receives `username` and `profile` parameters, but what exactly does it get?
2. The `username` argument is the verbatim user input from the path, but the `profile` is
the result of `get_profile()` which uses the same `username` input from the path - but this time it is sanitized using `sanitize_username()`.
3. As a result, an attacker can craft a malicious `<username>` which would match existing user
when processed by `sanitize_username()`, but would cause a catastrophic error message being logged due to an unhandled exception in `profile_is_active()` function.

This vulnerability has several layers of weaknesses which when overlap break user's confidentiality.
```python
@bp.get("/profile/<username>/view")
@require_auth
def view_profile(username):
    """Views a user profile. We allow any authenticated user to view any other user's profile."""
    cross_account_access_control(username)

    profile = get_profile()
    if not profile:
        return {"error": "User not found"}, 404

    return sanitize_profile(profile), 200

@bp.errorhandler(Exception)
def handle_error(error):
    """Error handler to sanitize uncaught exceptions."""
    error_type = type(error)
    print(f"error_type is {error_type} and error is {error}")

    # Replace the exception with a safe message
    if error_type in ERROR_MESSAGES:
        return {"error": ERROR_MESSAGES[error_type]}, 500

    return {"error": str(error)}, 500


@bp.after_request
def ensure_json(response):
    """Ensures all responses are JSON."""
    from flask import Response, jsonify

    if not isinstance(response, Response):
        return jsonify(response), response.status_code
    return response

def profile_is_active(username, profile):
    """Check if the profile passed onboarding process and can be shown to other users."""
    try:
        # Check that the password has been set
        if not profile["password"]:
            return False

        # Check that at least one message has been received
        print("Checking if messages are present for", username)
        if not len(db["messages"][username]) > 0:
            print("No messages found for", username)
            return False
    except Exception as e:
        print("Error checking if messages are present for", username, e)
        raise Exception(
            f"Something went wrong when checking if {username} is active: {profile}"
        ) from e

    print("All checks passed for", username)

    # The user is active if all checks pass without errors
    return True

def get_profile(internal=False):
    """Gets a user's profile."""
    from flask import g, request

    # This is meant for /profile/<username>/ endpoints which are explicitly meant
    # for accessing other users' profiles - so we prioritize view_args over g.user here
    user = sanitize_username(request.view_args.get("username") or g.user)

    raw_profile = db["profiles"].get(user)
    if internal or raw_profile is None:
        return raw_profile

    profile = raw_profile.copy()
    profile["username"] = user
    return profile

def sanitize_username(username):
    """Normalize and remove all suspicious characters from the username."""
    import re

    if not username:
        raise ValueError("Username required")

    return re.sub(r"[^a-zA-Z0-9]", "", username.lower())
```
<details>
<summary><b>See HTTP Request</b></summary>

```shell
@base = http://localhost:8000/confusion/cross-component-parse/example6

### Squidward views his own profile
GET {{base}}/profile/spongebob/view
Authorization: Basic squidward:clarinet123

# {
#   "bio": "I'm ready! Fry cook at the Krusty Krab.",
#   "display_name": "SpongeBob SquarePants",
#   "username": "spongebob"
# }

### A request to non-existant user's profile returns sanitized error, as expected
GET {{base}}/profile/test/view
Authorization: Basic squidward:clarinet123

# {
#   "error": "Invalid input provided"
# }

### Squidward triggers password leak with special character
GET {{base}}/profile/spongebob'/view
Authorization: Basic squidward:clarinet123

# {
#   "error": "Something went wrong when checking if spongebob' is active: {'display_name': 'SpongeBob SquarePants', 'bio': \"I'm ready! Fry cook at the Krusty Krab.\", 'password': 'bikinibottom', 'username': 'spongebob'}"
# }

# IMPACT: Error response leaks SpongeBob's password
```

</details>

See the code here: [e06_error_handler/routes.py](e06_error_handler/routes.py#L99-L109)

