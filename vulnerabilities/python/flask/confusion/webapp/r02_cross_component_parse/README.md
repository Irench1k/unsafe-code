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
| Baseline - Verbose Inline Authentication | [Example 1: Secure Baseline with Verbose Inline Authentication](#ex-1) | [e01_baseline/routes.py](e01_baseline/routes.py#L26-L147) |
| Middleware Introduction | [Example 2: Middleware with Source Precedence Bug](#ex-2) | [e02_middleware/routes.py](e02_middleware/routes.py#L39-L108) |
| Decorator with request.values | [Example 3: Decorator with request.values Confusion](#ex-3) | [e03_decorator/routes.py](e03_decorator/routes.py#L50-L79) |
| Fixed Decorator, Broken Handler | [Example 4: Handler Copies Old Decorator Logic](#ex-4) | [e04_decorator_reuses_g/routes.py](e04_decorator_reuses_g/routes.py#L45-L82) |
| Error Handler Patterns | [Example 5: Fail-Open Error Handler Leaks Passwords](#ex-5) | [e05_error_handler/routes.py](e05_error_handler/routes.py#L71-L90) |
| Basic Authentication Migration | [Example 6: Basic Authentication with Query Parameter Bug](#ex-6) | [e06_basic_auth/routes.py](e06_basic_auth/routes.py#L50-L94) |

## Baseline - Verbose Inline Authentication

Secure but repetitive authentication patterns that create pressure for refactoring. Every endpoint has 4-6 lines of identical authentication boilerplate:

1. Extract user and password from request.form
2. Call authenticate(user, password)
3. Return 401 if authentication fails
4. Proceed with business logic

This repetition makes code harder to maintain, increases copy-paste errors, and obscures business logic. Subsequent examples show various refactoring approaches and the subtle security issues they introduce.

### Example 1: Secure Baseline with Verbose Inline Authentication <a id="ex-1"></a>

Demonstrates secure but repetitive authentication. Every endpoint validates credentials inline with 4-6 lines of identical logic before executing business operations. This verbose pattern creates pressure to refactor into middleware or decorators, as shown in subsequent examples.
```python


@bp.post("/messages/list")
def list_messages():
    """Lists all messages for the authenticated user."""
    try:
        # Inline authentication (repeated in all endpoints)
        user = request.form.get("user")
        password = request.form.get("password")

        if not authenticate(user, password):
            return jsonify({"error": "Invalid credentials"}), 401

        # Business logic
        messages = get_messages(user)
        return jsonify({"user": user, "messages": messages}), 200
    except Exception:
        return jsonify({"error": "Failed to retrieve messages"}), 500


@bp.post("/messages/new")
def create_new_message():
    """Creates a new message from the authenticated user."""
    try:
        # Inline authentication (repeated)
        user = request.form.get("user")
        password = request.form.get("password")

        if not authenticate(user, password):
            return jsonify({"error": "Invalid credentials"}), 401

        # Business logic
        recipient = request.form.get("recipient")
        text = request.form.get("text", "")

        if not recipient:
            return jsonify({"error": "Recipient required"}), 400

        msg_id = create_message(sender=user, recipient=recipient, text=text)
        return (
            jsonify({"message_id": msg_id, "sender": user, "recipient": recipient}),
            201,
        )
    except Exception:
        return jsonify({"error": "Failed to create message"}), 500


@bp.patch("/messages/mark_read")
def mark_read():
    """Marks a message as read for the authenticated user."""
    try:
        # Inline authentication (repeated)
        user = request.form.get("user")
        password = request.form.get("password")

        if not authenticate(user, password):
            return jsonify({"error": "Invalid credentials"}), 401

        # Business logic
        message_id = request.form.get("message_id")
        if not message_id:
            return jsonify({"error": "message_id required"}), 400

        success = mark_message_read(int(message_id), user)
        if not success:
            return jsonify({"error": "Message not found or access denied"}), 404

        return jsonify({"message_id": message_id, "status": "read"}), 200
    except Exception:
        return jsonify({"error": "Failed to mark message"}), 500


@bp.post("/profile/view")
def view_profile():
    """Views a user profile (requires authentication)."""
    try:
        # Inline authentication (repeated)
        user = request.form.get("user")
        password = request.form.get("password")

        if not authenticate(user, password):
            return jsonify({"error": "Invalid credentials"}), 401

        # Business logic - can view any profile once authenticated
        profile_owner = request.form.get("profile_owner")
        if not profile_owner:
            return jsonify({"error": "profile_owner required"}), 400

        profile = get_profile(profile_owner)
        if not profile:
            return jsonify({"error": "User not found"}), 404

        return jsonify(profile), 200
    except Exception:
        return jsonify({"error": "Failed to retrieve profile"}), 500


@bp.patch("/profile/edit")
def edit_profile():
    """Edits the authenticated user's profile."""
    try:
        # Inline authentication (repeated)
        user = request.form.get("user")
        password = request.form.get("password")

        if not authenticate(user, password):
            return jsonify({"error": "Invalid credentials"}), 401

        # Business logic - can only edit own profile
        display_name = request.form.get("display_name")
        bio = request.form.get("bio")

        if not display_name and not bio:
            return jsonify({"error": "No updates provided"}), 400

        success = update_profile(user, display_name=display_name, bio=bio)
        if not success:
            return jsonify({"error": "Update failed"}), 500

        return jsonify({"status": "updated", "user": user}), 200
    except Exception:
        return jsonify({"error": "Failed to update profile"}), 500
```
<details>
<summary><b>See HTTP Request</b></summary>

```shell
### Example 1: Secure Baseline

### SpongeBob lists his messages
POST http://localhost:8000/confusion/cross-component-parse/example1/messages/list
Content-Type: application/x-www-form-urlencoded

user=spongebob&password=bikinibottom

###

### Squidward lists his messages
POST http://localhost:8000/confusion/cross-component-parse/example1/messages/list
Content-Type: application/x-www-form-urlencoded

user=squidward&password=clarinet123

###

### Attack fails with wrong credentials
POST http://localhost:8000/confusion/cross-component-parse/example1/messages/list
Content-Type: application/x-www-form-urlencoded

user=spongebob&password=wrong

# 401 Unauthorized
```

</details>

See the code here: [e01_baseline/routes.py](e01_baseline/routes.py#L26-L147)

## Middleware Introduction

Introduces Flask blueprint middleware to consolidate authentication into g.user. Explains Flask request lifecycle and g object. Contains source precedence bug where one handler reads from wrong source (request.args instead of request.form).

### Example 2: Middleware with Source Precedence Bug <a id="ex-2"></a>

Blueprint middleware validates credentials and stores the authenticated user in g.user. Most endpoints correctly use g.user, but profile/view accidentally reads profile_owner from request.args (query string) while middleware authenticates from request.form (body).

An attacker authenticates with their credentials in the form body, then specifies a victim's username in the query string to view their profile.
```python


@bp.post("/messages/list")
def list_messages():
    """Lists messages for authenticated user from g.user."""
    try:
        messages = get_messages(g.user)
        return jsonify({"user": g.user, "messages": messages}), 200
    except Exception:
        return jsonify({"error": "Failed to retrieve messages"}), 500


@bp.post("/messages/new")
def create_new_message():
    """Creates a message using g.user as sender."""
    try:
        recipient = request.form.get("recipient")
        text = request.form.get("text", "")

        if not recipient:
            return jsonify({"error": "Recipient required"}), 400

        msg_id = create_message(sender=g.user, recipient=recipient, text=text)
        return jsonify({"message_id": msg_id, "sender": g.user}), 201
    except Exception:
        return jsonify({"error": "Failed to create message"}), 500


@bp.post("/profile/view")
def view_profile():
    """
    Views a profile - VULNERABLE!

    This endpoint was accidentally changed during refactoring. It reads profile_owner
    from request.args instead of request.form, while middleware authenticates
    using form data.
    """
    try:
        # BUG: Should use request.form.get("profile_owner")
        profile_owner = request.args.get("profile_owner")

        if not profile_owner:
            return jsonify({"error": "profile_owner required"}), 400

        profile = get_profile(profile_owner)
        if not profile:
            return jsonify({"error": "User not found"}), 404

        return jsonify(profile), 200
    except Exception:
        return jsonify({"error": "Failed to retrieve profile"}), 500


@bp.patch("/profile/edit")
def edit_profile():
    """Edits authenticated user's profile using g.user."""
    try:
        display_name = request.form.get("display_name")
        bio = request.form.get("bio")

        if not display_name and not bio:
            return jsonify({"error": "No updates provided"}), 400

        success = update_profile(g.user, display_name=display_name, bio=bio)
        if not success:
            return jsonify({"error": "Update failed"}), 500

        return jsonify({"status": "updated", "user": g.user}), 200
    except Exception:
        return jsonify({"error": "Failed to update profile"}), 500
```
<details>
<summary><b>See HTTP Request</b></summary>

```shell
@base = http://localhost:8000/confusion/cross-component-parse/example2

### Squidward views his own profile
POST {{base}}/profile/view
Content-Type: application/x-www-form-urlencoded

user=squidward&password=clarinet123&profile_owner=squidward

###

### Squidward views SpongeBob's profile via source precedence
POST {{base}}/profile/view?profile_owner=spongebob
Content-Type: application/x-www-form-urlencoded

user=squidward&password=clarinet123&profile_owner=squidward

# IMPACT: Squidward views SpongeBob's profile
# Middleware authenticates from form body, handler reads target from query string
```

</details>

See the code here: [e02_middleware/routes.py](e02_middleware/routes.py#L39-L108)

## Decorator with request.values

Adds authentication decorator using request.values for "flexibility", creating precedence confusion similar to r01's examples. Middleware sets g.user from request.form while decorator validates from request.values (args take precedence).

### Example 3: Decorator with request.values Confusion <a id="ex-3"></a>

Authentication decorator uses request.values for "flexibility", which combines args and form with args taking precedence. Middleware sets g.user from request.form only.

Attack: Provide credentials in query string (args), victim's name in form body. Decorator authenticates attacker via request.values (finds args first), middleware sets g.user from form (victim's name), handler operates on g.user (victim).
```python


@bp.post("/messages/list")
@require_auth
def list_messages():
    """Lists messages - uses g.user set by middleware."""
    try:
        messages = get_messages(g.user)
        return jsonify({"user": g.user, "messages": messages}), 200
    except Exception:
        return jsonify({"error": "Failed"}), 500


@bp.patch("/profile/edit")
@require_auth
def edit_profile():
    """Edits profile using g.user - VULNERABLE!"""
    try:
        display_name = request.form.get("display_name")
        bio = request.form.get("bio")

        if not display_name and not bio:
            return jsonify({"error": "No updates provided"}), 400

        # Uses g.user which was set by middleware from request.form
        success = update_profile(g.user, display_name=display_name, bio=bio)

        return jsonify({"status": "updated", "user": g.user}), 200
    except Exception:
        return jsonify({"error": "Failed"}), 500
```
<details>
<summary><b>See HTTP Request</b></summary>

```shell
@base = http://localhost:8000/confusion/cross-component-parse/example3

### Squidward lists his messages
POST {{base}}/messages/list
Content-Type: application/x-www-form-urlencoded

user=squidward&password=clarinet123

###

### Squidward edits SpongeBob's profile via request.values confusion
PATCH {{base}}/profile/edit?user=squidward&password=clarinet123
Content-Type: application/x-www-form-urlencoded

user=spongebob&display_name=Squidward was here&bio=Hacked!

# IMPACT: SpongeBob's profile defaced
# Decorator authenticates from request.values (args), middleware sets g.user from form
```

</details>

See the code here: [e03_decorator/routes.py](e03_decorator/routes.py#L50-L79)

## Fixed Decorator, Broken Handler

Decorator is "fixed" to reuse g.user from middleware (secure!), but a new handler copies the old decorator's buggy logic inline. Demonstrates how copy-paste programming reintroduces fixed vulnerabilities.

### Example 4: Handler Copies Old Decorator Logic <a id="ex-4"></a>

The decorator was fixed to reuse g.user from middleware, eliminating precedence confusion. However, when adding delete_messages, a developer copied the OLD decorator's logic directly into the handler for "flexibility", reading credentials from request.args while middleware sets g.user from request.form.
```python


@bp.patch("/profile/edit")
@require_auth
def edit_profile():
    """Securely edits profile using fixed decorator."""
    try:
        display_name = request.form.get("display_name")
        bio = request.form.get("bio")

        success = update_profile(g.user, display_name=display_name, bio=bio)
        return jsonify({"status": "updated"}), 200
    except Exception:
        return jsonify({"error": "Failed"}), 500


@bp.delete("/messages/delete_all")
def delete_all_messages():
    """
    Deletes all messages for a user.

    VULNERABLE: Copied old authentication pattern inline instead of
    using the fixed require_auth decorator.
    """
    try:
        # Inline auth (copied from old decorator code)
        username = request.args.get("username")  # BUG: Should use g.user
        password = request.args.get("password")

        if not authenticate(username, password):
            return jsonify({"error": "Invalid credentials"}), 401

        # Business logic uses g.user (set by middleware from form!)
        count = delete_messages(g.user)

        return jsonify({"status": "deleted", "count": count}), 200
    except Exception:
        return jsonify({"error": "Failed"}), 500
```
<details>
<summary><b>See HTTP Request</b></summary>

```shell
@base = http://localhost:8000/confusion/cross-component-parse/example4

### Plankton deletes his own messages
DELETE {{base}}/messages/delete_all?username=plankton&password=chumbucket
Content-Type: application/x-www-form-urlencoded

username=plankton

###

### Plankton deletes Mr. Krabs' messages via inline auth bug
DELETE {{base}}/messages/delete_all?username=plankton&password=chumbucket
Content-Type: application/x-www-form-urlencoded

username=mr.krabs

# IMPACT: Mr. Krabs' messages deleted
# Handler authenticates from args, middleware sets g.user from form, deletion uses g.user
```

</details>

See the code here: [e04_decorator_reuses_g/routes.py](e04_decorator_reuses_g/routes.py#L45-L82)

## Error Handler Patterns

Introduces errorhandler with fail-open vulnerability. Known exceptions map to safe messages, but unexpected exceptions expose full details including passwords. Demonstrates information disclosure through defensive-looking error handling.

### Example 5: Fail-Open Error Handler Leaks Passwords <a id="ex-5"></a>

Error handler maps known exceptions to safe messages but fails open for unexpected exceptions, revealing full error details. The validate_username_format function includes the full profile (with password) in RuntimeError exceptions.

When an attacker provides a username with suspicious characters, it triggers an unknown exception type that leaks the password in the error response.
```python


@bp.get("/profile/view")
@require_auth
def view_profile():
    """
    Views a profile - vulnerable to information disclosure via error handling.
    """
    profile_owner = request.args.get("username")
    if not profile_owner:
        return {"error": "username required"}, 400

    # Validate BEFORE fetching (triggers exception with profile data)
    validate_username_format(profile_owner)

    profile = get_profile_internal(profile_owner)
    if not profile:
        return {"error": "User not found"}, 404

    return sanitize_profile(profile), 200
```
<details>
<summary><b>See HTTP Request</b></summary>

```shell
@base = http://localhost:8000/confusion/cross-component-parse/example5

### Squidward views his own profile (safe)
GET {{base}}/profile/view?username=squidward
Content-Type: application/x-www-form-urlencoded

username=squidward&password=clarinet123

###

### Squidward triggers password leak with special character
GET {{base}}/profile/view?username=spongebob'
Content-Type: application/x-www-form-urlencoded

username=squidward&password=clarinet123

# IMPACT: Error response leaks SpongeBob's password
# Validation triggers RuntimeError with full profile, fail-open handler exposes details
```

</details>

See the code here: [e05_error_handler/routes.py](e05_error_handler/routes.py#L71-L90)

## Basic Authentication Migration

Modernizes to HTTP Basic Auth via Authorization header. Most endpoints correctly use g.user, but one handler reads username from query string instead, enabling authenticated users to view any profile.

### Example 6: Basic Authentication with Query Parameter Bug <a id="ex-6"></a>

Modernized authentication using HTTP Basic Auth via Authorization header. Most endpoints correctly use g.user, but profile/view reads username from query string instead, enabling authenticated users to view any profile by specifying a different username in the URL.
```python


@bp.get("/messages/list")
@require_auth
def list_messages():
    """Lists messages using g.user from decorator."""
    messages = get_messages(g.user)
    return {"user": g.user, "messages": messages}, 200


@bp.patch("/profile/edit")
@require_auth
def edit_profile():
    """Edits authenticated user's profile."""
    display_name = request.form.get("display_name")
    bio = request.form.get("bio")

    if not display_name and not bio:
        return {"error": "No updates provided"}, 400

    update_profile(g.user, display_name=display_name, bio=bio)
    return {"status": "updated", "user": g.user}, 200


@bp.get("/profile/view")
@require_auth
def view_profile():
    """
    Views any user's profile - VULNERABLE!

    Reads username from query parameter instead of using g.user or validating
    that the requested user matches the authenticated user.
    """
    # BUG: Should use g.user (authenticated user can view their own)
    # OR validate username == g.user
    username = request.args.get("username")

    if not username:
        return {"error": "username required"}, 400

    profile = get_profile(username)
    if not profile:
        return {"error": "User not found"}, 404

    return profile, 200
```
<details>
<summary><b>See HTTP Request</b></summary>

```shell
@base = http://localhost:8000/confusion/cross-component-parse/example6

### Squidward views his own profile
GET {{base}}/profile/view?username=squidward
Authorization: Basic squidward clarinet123

###

### Squidward views SpongeBob's profile via query parameter
GET {{base}}/profile/view?username=spongebob
Authorization: Basic squidward clarinet123

# IMPACT: Squidward views SpongeBob's profile
# Authorization header authenticates Squidward, handler reads username from query string
```

</details>

See the code here: [e06_basic_auth/routes.py](e06_basic_auth/routes.py#L50-L94)
