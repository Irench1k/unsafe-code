# Source Precedence Drift in Flask

When authentication trusts one request container and the handler trusts another, attackers can swap values between query strings, form bodies, JSON, or path params.

## Overview

Source precedence bugs creep in when two parts of the stack read the "same" input from different sources. Flask makes this easy: query strings, HTML form bodies, JSON payloads, and path parameters each land in different containers, and helpers like `request.values` silently merge them with their own priority rules.

**Common causes:**
- Security code in decorators or helpers reads from `request.args` while the view trusts `request.form` or `request.get_json()`.
- Refactors that move from query parameters to JSON do not update the guard.
- Tests rarely cover both body and query variants, so the inconsistency remains hidden until production.

**Review checklist:**
1. Identify every lookup of the relevant key (e.g. `user`, `group`, `account_id`).
2. Note whether it comes from `.args`, `.form`, `.view_args`, `.json`, or `.values`.
3. Confirm the security decision and the business logic read from the same place, or explicitly reconcile them before use.

## Table of Contents

| Category | Example | File |
|:---:|:---:|:---:|
| Secure Baselines | [Example 1: Secure Implementation](#ex-1) | [e0103_intro/routes.py](e0103_intro/routes.py#L33-L51) |
| Straightforward Source Drift | [Example 2: Basic Parameter Source Confusion](#ex-2) | [e0103_intro/routes.py](e0103_intro/routes.py#L68-L87) |
| Straightforward Source Drift | [Example 3: Function-Level Parameter Source Confusion](#ex-3) | [e0103_intro/routes.py](e0103_intro/routes.py#L97-L126) |
| Straightforward Source Drift | [Example 4: Cross-Module Parameter Source Confusion](#ex-4) | [e04_cross_module/db.py](e04_cross_module/db.py#L50-L71) |
| Helper-Induced Mixing | [Example 5: Mixed-Source Authentication](#ex-5) | [e0506_variations/routes.py](e0506_variations/routes.py#L69-L106) |
| Helper-Induced Mixing | [Example 6: Destructive Parameter Source Confusion](#ex-6) | [e0506_variations/routes.py](e0506_variations/routes.py#L129-L151) |
| request.values Footguns | [Example 7: Form Authentication Bypass](#ex-7) | [e0708_apparent_fix/routes.py](e0708_apparent_fix/routes.py#L77-L103) |
| request.values Footguns | [Example 8: Password Reset Parameter Confusion](#ex-8) | [e0708_apparent_fix/routes.py](e0708_apparent_fix/routes.py#L150-L170) |

## Secure Baselines

Consistent usage keeps authentication and data access aligned - use these to understand the intended flow before exploring the vulnerable variants.

### Example 1: Secure Implementation <a id="ex-1"></a>

Here you can see a secure implementation that consistently uses query string parameters for both authentication and data retrieval.
```python
@bp.route("/example1", methods=["GET", "POST"])
def example1():
    """
    Retrieves messages for an authenticated user.

    Uses query string parameters for both authentication and message retrieval,
    ensuring consistent parameter sourcing throughout the request lifecycle.
    """
    user = request.args.get("user", None)

    password = db["passwords"].get(user, None)
    if password is None or password != request.args.get("password", None):
        return "Invalid user or password", 401

    messages = db["messages"].get(user, None)
    if messages is None:
        return "No messages found", 404

    return messages
```
<details open>
<summary><b>See HTTP Request</b></summary>

```shell
### SpongeBob accesses his own messages
GET http://localhost:8000/confusion/source-precedence/example1?user=spongebob&password=bikinibottom

# Results in 200 OK:
#
# [
#   {
#     "from": "patrick",
#     "message": "SpongeBob! I'm ready! I'm ready! Let's go jellyfishing!"
#   }
# ]

###

### Squidward accesses his own messages
GET http://localhost:8000/confusion/source-precedence/example1?user=squidward&password=clarinet123

# Results in 200 OK:
#
# [
#   {
#     "from": "mr.krabs",
#     "message": "Squidward, I'm switching yer shifts to Tuesday through Saturday. No complaints!"
#   },
#   {
#     "from": "squidward",
#     "message": "Note to self: Mr. Krabs hides the safe key under the register. Combination is his first dime's serial number."
#   }
# ]

###

### Squidward tries to access SpongeBob's messages but doesn't know the password
GET http://localhost:8000/confusion/source-precedence/example1?user=spongebob&password=wrong-password

# Results in 401 Unauthorized:
#
# Invalid user or password
```
</details>

## Straightforward Source Drift

Simple handlers where the guard inspects query parameters but the action trusts form data or vice versa.

### Example 2: Basic Parameter Source Confusion <a id="ex-2"></a>

Demonstrates the most basic form of parameter source confusion where authentication uses **query** parameters but data retrieval uses **form** data.

We take the user name from the query string during the validation, but during the data retrieval another value is used, taken from the request body (form). This does not look very realistic, but it demonstrates the core of the vulnerability, we will build upon this further.

Here you can see if we provide squidward's name in the request body, we can access his messages without his password.
```python
@bp.route("/example2", methods=["GET", "POST"])
def example2():
    """
    Retrieves messages for an authenticated user.

    Supports flexible parameter passing to accommodate various client implementations.
    """
    user = request.args.get("user", None)

    password = db["passwords"].get(user, None)
    if password is None or password != request.args.get("password", None):
        return "Invalid user or password", 401

    # Allow form data to specify the target user for message retrieval
    user = request.form.get("user", None)
    messages = db["messages"].get(user, None)
    if messages is None:
        return "No messages found", 404

    return messages
```
<details>
<summary><b>See HTTP Request</b></summary>

```shell
### Squidward accesses his own messages
GET http://localhost:8000/confusion/source-precedence/example2?user=squidward&password=clarinet123
Content-Type: application/x-www-form-urlencoded

user=squidward

# Results in 200 OK:
#
# [
#   {
#     "from": "mr.krabs",
#     "message": "Squidward, I'm switching yer shifts to Tuesday through Saturday. No complaints!"
#   },
#   {
#     "from": "squidward",
#     "message": "Note to self: Mr. Krabs hides the safe key under the register. Combination is his first dime's serial number."
#   }
# ]

###

### Why are we sending the same username twice? I wonder what would happen if I changed one...
GET http://localhost:8000/confusion/source-precedence/example2?user=squidward&password=clarinet123
Content-Type: application/x-www-form-urlencoded

user=spongebob

# Results in unauthorized data access:
#
# [
#   {
#     "from": "patrick",
#     "message": "SpongeBob! I'm ready! I'm ready! Let's go jellyfishing!"
#   }
# ]
#
# Squidward accessed SpongeBob's messages using his own password!
```

</details>

### Example 3: Function-Level Parameter Source Confusion <a id="ex-3"></a>

Functionally equivalent to example 2, but shows how separating authentication and data retrieval into different functions can make the vulnerability harder to spot.
```python
def authenticate(user, password):
    """Validates user credentials against the database."""
    return password is not None and password == db["passwords"].get(user, None)


def get_messages(user):
    """Retrieves all messages for the specified user."""
    messages = db["messages"].get(user, None)
    if messages is None:
        return None
    return {"owner": user, "messages": messages}


@bp.route("/example3", methods=["GET", "POST"])
def example3():
    """
    Retrieves messages for an authenticated user.

    Uses modular authentication and data retrieval functions for cleaner separation of concerns.
    """
    if not authenticate(
        request.args.get("user", None), request.args.get("password", None)
    ):
        return "Invalid user or password", 401

    messages = get_messages(request.form.get("user", None))
    if messages is None:
        return "No messages found", 404

    return messages
```
<details open>
<summary><b>See HTTP Request</b></summary>

```shell
@base = http://localhost:8000/confusion/source-precedence

### Squidward accesses his own messages
GET {{base}}/example3?user=squidward&password=clarinet123
Content-Type: application/x-www-form-urlencoded

user=squidward

# Results in 200 OK:
#
# {
#   "owner": "squidward",
#   "messages": [
#     {
#       "from": "mr.krabs",
#       "message": "Squidward, I'm switching yer shifts to Tuesday through Saturday. No complaints!"
#     },
#     {
#       "from": "squidward",
#       "message": "Note to self: Mr. Krabs hides the safe key under the register. Combination is his first dime's serial number."
#     }
#   ]
# }

###

### Why are we sending the same username twice? I wonder what would happen if I changed one...
GET {{base}}/example3?user=squidward&password=clarinet123
Content-Type: application/x-www-form-urlencoded

user=spongebob

# Results in unauthorized data access:
#
# {
#   "owner": "spongebob",
#   "messages": [
#     {
#       "from": "patrick",
#       "message": "SpongeBob! I'm ready! I'm ready! Let's go jellyfishing!"
#     }
#   ]
# }
#
# Same vulnerability despite refactoring into separate functions!
```
</details>

### Example 4: Cross-Module Parameter Source Confusion <a id="ex-4"></a>

In the previous example, you can still see that the `user` value gets retrieved from the `request.args` during validation but from the `request.form` during data retrieval.

A more subtle example, where this is not immediately obvious (imagine, `authenticate_user` is defined in an another file altogether):
```python
def authenticate(user, password):
    """Validates user credentials against the database."""
    return password is not None and password == db["passwords"].get(user, None)


def get_messages(user):
    """Retrieves all messages for the specified user."""
    messages = db["messages"].get(user, None)
    if messages is None:
        return None
    return {"owner": user, "messages": messages}


def authenticate_user():
    """
    Authenticates the current user using query string credentials.

    Designed for GET-based authentication flows where credentials are passed in the URL.
    """
    return authenticate(
        request.args.get("user", None), request.args.get("password", None)
    )

@bp.route("/example4", methods=["GET", "POST"])
def example4():
    """
    Retrieves messages for an authenticated user.

    Delegates authentication to a shared utility function while handling
    message retrieval directly in the endpoint.
    """
    if not authenticate_user():
        return "Invalid user or password", 401

    messages = get_messages(request.form.get("user", None))
    if messages is None:
        return "No messages found", 404

    return messages
```
<details>
<summary><b>See HTTP Request</b></summary>

```shell
@base = http://localhost:8000/confusion/source-precedence

### Plankton accesses his own messages
GET {{base}}/example4?user=plankton&password=chumbucket
Content-Type: application/x-www-form-urlencoded

user=plankton

# Results in 200 OK:
#
# {
#   "owner": "plankton",
#   "messages": [
#     {
#       "from": "karen",
#       "message": "Plankton, your plan to hack the Krusty Krab is ready. I've set up the proxy server."
#     }
#   ]
# }

###

### The vulnerability persists even with code split across modules!
GET {{base}}/example4?user=plankton&password=chumbucket
Content-Type: application/x-www-form-urlencoded

user=squidward

# Results in unauthorized access:
#
# {
#   "owner": "squidward",
#   "messages": [
#     {
#       "from": "mr.krabs",
#       "message": "Squidward, I'm switching yer shifts to Tuesday through Saturday. No complaints!"
#     },
#     {
#       "from": "squidward",
#       "message": "Note to self: Mr. Krabs hides the safe key under the register. Combination is his first dime's serial number."
#     }
#   ]
# }
#
# Plankton learned where Mr. Krabs hides the safe key!
```

</details>

## Helper-Induced Mixing

Utility functions that merge sources (or hide precedence rules) create subtle inconsistencies developers rarely spot in review.

### Example 5: Mixed-Source Authentication <a id="ex-5"></a>

Shows how authentication and data access can use different combinations of sources.

This one is interesting, because you can access Squidward's messages by providing his username and SpongeBob's password in the request query, while providing SpongeBob's username in the request body:
```python
def get_user():
    """
    Retrieves the user identifier from the request.

    Checks form data first for POST requests, falling back to query parameters
    to support both form submissions and direct URL access.
    """
    user_from_form = request.form.get("user", None)
    user_from_args = request.args.get("user", None)

    return user_from_form or user_from_args


def authenticate_user_example5():
    """
    Authenticates the current user with flexible parameter resolution.

    Uses the user resolution helper for username while taking password from query string.
    """
    user = get_user()
    password = request.args.get("password", None)
    return authenticate(user, password)


@bp.route("/example5", methods=["GET", "POST"])
def example5():
    """
    Retrieves messages for an authenticated user.

    Combines flexible authentication with query-based message retrieval.
    """
    if not authenticate_user_example5():
        return "Invalid user or password", 401

    messages = get_messages(request.args.get("user", None))
    if messages is None:
        return "No messages found", 404
    return messages
```
<details>
<summary><b>See HTTP Request</b></summary>

```shell
@base = http://localhost:8000/confusion/source-precedence

### Squidward accesses his own messages
GET {{base}}/example5?user=squidward&password=clarinet123

# Results in 200 OK:
#
# {
#   "owner": "squidward",
#   "messages": [
#     {
#       "from": "mr.krabs",
#       "message": "Squidward, I'm switching yer shifts to Tuesday through Saturday. No complaints!"
#     },
#     {
#       "from": "squidward",
#       "message": "Note to self: Mr. Krabs hides the safe key under the register. Combination is his first dime's serial number."
#     }
#   ]
# }

###

### Remember when we sent the username twice in Example 2? This looks more secure - only one username!
### Hm, I wonder if the server would still accept the old trick, just reversed...
GET {{base}}/example5?user=spongebob&password=clarinet123
Content-Type: application/x-www-form-urlencoded

user=squidward

# Results in unauthorized access:
#
# {
#   "owner": "spongebob",
#   "messages": [
#     {
#       "from": "patrick",
#       "message": "SpongeBob! I'm ready! I'm ready! Let's go jellyfishing!"
#     }
#   ]
# }
#
# The exploit STILL works, just with reversed precedence!
```

</details>

### Example 6: Destructive Parameter Source Confusion <a id="ex-6"></a>

Demonstrates parameter source confusion with a DELETE operation. Same root cause as Examples 2-5, but now enabling destructive operations instead of just data disclosure. Authentication uses query parameters while deletion target uses form body.
```python
@bp.route("/example6", methods=["DELETE", "GET"])
def example6():
    """Manages user messages with list and delete operations."""
    if not authenticate_user():
        return "Invalid user or password", 401

    action = request.args.get("action", "delete")

    if action == "list":
        user = request.args.get("user")
        messages = get_messages(user)
        if messages is None:
            return "No messages found", 404
        return messages

    # Delete message - target user from form body (VULNERABILITY)
    target_user = request.form.get("user")
    message_index = int(request.args.get("index", 0))

    if delete_message(target_user, message_index):
        return {"status": "deleted", "user": target_user, "index": message_index}
    else:
        return "Message not found", 404
```
<details>
<summary><b>See HTTP Request</b></summary>

```shell
@base = http://localhost:8000/confusion/source-precedence

### Mr. Krabs checks his inbox for security warnings
GET {{base}}/example6?user=mr.krabs&password=money&action=list

# Results in 200 OK:
#
# {
#   "owner": "mr.krabs",
#   "messages": [
#     {
#       "from": "squidward",
#       "message": "I saw Plankton buying a mechanical keyboard, he's planning to hack us!"
#     }
#   ]
# }

###

### Plankton deletes Mr. Krabs' warning message using his own credentials!
DELETE {{base}}/example6?user=plankton&password=chumbucket&index=0
Content-Type: application/x-www-form-urlencoded

user=mr.krabs

# Results in successful deletion:
#
# {
#   "status": "deleted",
#   "user": "mr.krabs",
#   "index": 0
# }
#
# Plankton covered his tracks! Same vulnerability, but now enabling destructive operations.

###

### Mr. Krabs checks his inbox again - the warning is gone!
GET {{base}}/example6?user=mr.krabs&password=money&action=list

# Results in empty inbox:
#
# {
#   "owner": "mr.krabs",
#   "messages": []
# }
```

</details>

## request.values Footguns

`request.values` promises convenience but applies its own precedence rules, leading to silent bypasses when paired with explicit `.args` or `.form` lookups.

### Example 7: Form Authentication Bypass <a id="ex-7"></a>

The endpoint uses form data for authentication, but request.values.get() allows query parameters to override form values, creating a vulnerability. Although designed for POST requests, the endpoint accepts both GET and POST methods, enabling the attack.

Note that although the regular usage would rely on POST request (or PUT, PATCH, etc.), and wouldn't work with GET (because flask's request.values ignores form data in GET requests), the attacker can send both GET and POST requests (if the endpoint is configured to accept both methods).

```http
POST /ii/source-precedence/example7? HTTP/1.1
Content-Type: application/x-www-form-urlencoded
Content-Length: 35

user=spongebob&password=bikinibottom
```

However, the attacker can send both GET and POST requests (if the endpoint is configured to accept both methods).
```python
def authenticate_user_example7():
    """
    Authenticates the user using form-based credentials.

    Designed for POST-based form submissions where credentials are in the request body.
    """
    return authenticate(
        request.form.get("user", None), request.form.get("password", None)
    )


@bp.route("/example7", methods=["GET", "POST"])
def example7():
    """
    Retrieves messages for an authenticated user.

    Uses form-based authentication with unified parameter resolution for message retrieval.
    """
    if not authenticate_user_example7():
        return "Invalid user or password", 401

    # Use request.values for flexible parameter resolution across query and form data
    messages = get_messages(request.values.get("user", None))
    if messages is None:
        return "No messages found", 404

    return messages
```
<details>
<summary><b>See HTTP Request</b></summary>

```shell
@base = http://localhost:8000/confusion/source-precedence

### Squidward logs in using form body (BEST PRACTICE - credentials not logged in URLs!)
POST {{base}}/example7
Content-Type: application/x-www-form-urlencoded

user=squidward&password=clarinet123

# Results in 200 OK:
#
# {
#   "owner": "squidward",
#   "messages": [
#     {
#       "from": "mr.krabs",
#       "message": "Squidward, I'm switching yer shifts to Tuesday through Saturday. No complaints!"
#     },
#     {
#       "from": "squidward",
#       "message": "Note to self: Mr. Krabs hides the safe key under the register. Combination is his first dime's serial number."
#     }
#   ]
# }

###

### Despite using secure form-body authentication, the endpoint is still vulnerable!
POST {{base}}/example7?user=spongebob
Content-Type: application/x-www-form-urlencoded

user=squidward&password=clarinet123

# Results in unauthorized access:
#
# {
#   "owner": "spongebob",
#   "messages": [
#     {
#       "from": "patrick",
#       "message": "SpongeBob! I'm ready! I'm ready! Let's go jellyfishing!"
#     }
#   ]
# }
#
# Squidward accessed SpongeBob's messages! Using form body for auth is best practice,
# but request.values in retrieval still merges query+form parameters.
```

</details>

### Example 8: Password Reset Parameter Confusion <a id="ex-8"></a>

Developers "fixed" the messages endpoint but introduced a NEW vulnerability when adding password reset functionality. Authentication uses request.values to verify WHO is making the request, but the target user whose password gets reset comes from request.form only.

An attacker can authenticate with their own credentials in the query string while specifying a victim's username in the form body, resetting the victim's password to one they control. This enables full account takeover.

LESSON: This demonstrates how "apparent fixes" create false security. Same root cause as Examples 2-7, but now enabling account takeover instead of just data disclosure. The partial fix made developers careless when adding new features.
```python
@bp.route("/example8/password_reset", methods=["POST"])
def example8_password_reset():
    """Resets a user's password after authentication."""
    # Authenticate using merged values (who's making the request)
    auth_user = request.values.get("user", None)
    auth_password = request.values.get("password", None)

    if not authenticate(auth_user, auth_password):
        return "Invalid user or password", 401

    # Target user and new password from form data (VULNERABILITY)
    target_user = request.form.get("user", None)
    new_password = request.form.get("new_password", None)

    if target_user is None or new_password is None:
        return "Missing required parameters", 400

    if reset_password(target_user, new_password):
        return {"status": "success", "user": target_user, "message": "Password updated"}
    else:
        return "User not found", 404
```
<details>
<summary><b>See HTTP Request</b></summary>

```shell
@base = http://localhost:8000/confusion/source-precedence

### Squidward checks his own messages with the FIXED endpoint
POST {{base}}/example8
Content-Type: application/x-www-form-urlencoded

user=squidward&password=clarinet123

# Results in 200 OK:
#
# {
#   "owner": "squidward",
#   "messages": [
#     {
#       "from": "mr.krabs",
#       "message": "Squidward, I'm switching yer shifts to Tuesday through Saturday. No complaints!"
#     },
#     {
#       "from": "squidward",
#       "message": "Note to self: Mr. Krabs hides the safe key under the register. Combination is his first dime's serial number."
#     }
#   ]
# }

###

### Squidward tries his old Example 7 exploit - but they fixed it!
POST {{base}}/example8?user=spongebob
Content-Type: application/x-www-form-urlencoded

user=squidward&password=clarinet123

# Results in 401 Unauthorized:
#
# Invalid user or password
#
# The old trick doesn't work anymore. They're using request.values consistently now.

###

### Plankton discovers the NEW password reset endpoint
POST {{base}}/example8/password_reset?user=plankton&password=chumbucket
Content-Type: application/x-www-form-urlencoded

user=squidward&new_password=hacked123

# Results in successful password change:
#
# {
#   "status": "success",
#   "user": "squidward",
#   "message": "Password updated"
# }
#
# The developers made the SAME mistake in their new feature!

###

### Plankton logs into Squidward's account with the new password
POST {{base}}/example8
Content-Type: application/x-www-form-urlencoded

user=squidward&password=hacked123

# Results in full account takeover:
#
# {
#   "owner": "squidward",
#   "messages": [
#     {
#       "from": "mr.krabs",
#       "message": "Squidward, I'm switching yer shifts to Tuesday through Saturday. No complaints!"
#     },
#     {
#       "from": "squidward",
#       "message": "Note to self: Mr. Krabs hides the safe key under the register. Combination is his first dime's serial number."
#     }
#   ]
# }
#
# Account takeover! Not just reading data anymore - Plankton now OWNS Squidward's account.
# Same root cause as Examples 2-7, but the "fix" gave developers false confidence.
```

</details>

