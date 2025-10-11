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
| Secure Baselines | [Example 1: Secure Implementation](#ex-1) | [e00_intro/routes.py](e00_intro/routes.py#L32-L45) |
| Straightforward Source Drift | [Example 2: Inline request.form vs request.args Confusion](#ex-2) | [e00_intro/routes.py](e00_intro/routes.py#L58-L69) |
| Straightforward Source Drift | [Example 3: Function-Level Parameter Source Confusion](#ex-3) | [e00_intro/routes.py](e00_intro/routes.py#L79-L105) |
| Straightforward Source Drift | [Example 4: Cross-Module Parameter Source Confusion](#ex-4) | [e04_cross_module/routes.py](e04_cross_module/routes.py#L22-L33) |
| Helper-Induced Mixing | [Example 5: Truthy-OR Parameter Precedence](#ex-5) | [e05_truthy_or/routes.py](e05_truthy_or/routes.py#L34-L50) |
| Helper-Induced Mixing | [Example 6: dict.get() Default Parameter Precedence](#ex-6) | [e06_dict_get_default/routes.py](e06_dict_get_default/routes.py#L21-L31) |
| request.values Footguns | [Example 7: Flask's request.values Precedence Rules](#ex-7) | [e07_request_values/routes.py](e07_request_values/routes.py#L24-L38) |
| request.values Footguns | [Example 8: Inconsistent request.values Adoption](#ex-8) | [e08_inconsistent_adoption/routes.py](e08_inconsistent_adoption/routes.py#L37-L60) |

## Secure Baselines

Consistent usage keeps authentication and data access aligned - use these to understand the intended flow before exploring the vulnerable variants.

### Example 1: Secure Implementation <a id="ex-1"></a>

Here you can see a secure implementation that consistently uses form body parameters for both authentication and data retrieval.
```python
@bp.post("/example1")
def example1():
    """Retrieves messages for an authenticated user."""
    user = request.form.get("user")
    if not user:
        return "Invalid user or password", 401

    password = db["passwords"].get(user)
    if not password or password != request.form.get("password"):
        return "Invalid user or password", 401

    messages = db["messages"].get(user, [])

    return messages
```
<details>
<summary><b>See HTTP Request</b></summary>

```shell
### SpongeBob accesses his own messages
POST http://localhost:8000/confusion/source-precedence/example1
Content-Type: application/x-www-form-urlencoded

user=spongebob&password=bikinibottom

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
POST http://localhost:8000/confusion/source-precedence/example1
Content-Type: application/x-www-form-urlencoded

user=squidward&password=clarinet123

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
POST http://localhost:8000/confusion/source-precedence/example1
Content-Type: application/x-www-form-urlencoded

user=spongebob&password=wrong-password

# Results in 401 Unauthorized:
#
# Invalid user or password
```

</details>

## Straightforward Source Drift

Simple handlers where the guard inspects query parameters but the action trusts form data or vice versa.

**Technical note:** While query parameters are commonly associated with GET requests, POST requests can include both query strings and request bodies. Flask parses both sources regardless of HTTP method, enabling these attacks.

### Example 2: Inline request.form vs request.args Confusion <a id="ex-2"></a>

Demonstrates the most basic form of parameter source confusion where authentication uses **form body** parameters but data retrieval uses **query string** parameters.

An attacker authenticates with their own credentials in the body while specifying a victim's username in the URL.
```python
@bp.post("/example2")
def example2():
    """Retrieves messages for an authenticated user."""
    # Verify that user is authenticated
    password = db["passwords"].get(request.form.get("user"))
    if not password or password != request.form.get("password"):
        return "Invalid user or password", 401

    # Retrieve messages for the authenticated user
    messages = db["messages"].get(request.args.get("user"), [])

    return messages
```
<details>
<summary><b>See HTTP Request</b></summary>

```shell
### Squidward accesses his own messages
POST http://localhost:8000/confusion/source-precedence/example2?user=squidward
Content-Type: application/x-www-form-urlencoded


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
POST http://localhost:8000/confusion/source-precedence/example2?user=spongebob
Content-Type: application/x-www-form-urlencoded

user=squidward&password=clarinet123

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

Separating authentication and data retrieval into different functions can make the vulnerability harder to spot.
```python
@bp.post("/example3")
def example3():
    """
    Retrieves messages for an authenticated user.

    Uses modular authentication and data retrieval functions for cleaner separation of concerns.
    """
    principal = resolve_principal(request)
    if not authenticate(principal, request.form.get("password")):
        return "Invalid user or password", 401
    return messages_get(request)


def messages_get(request):
    """Retrieves all messages for the specified user."""
    messages = db["messages"].get(request.form.get("user"), [])
    return messages


def authenticate(principal, password):
    """Validates user credentials against the database."""
    return password and password == db["passwords"].get(principal)


def resolve_principal(request):
    """Resolves the principal from the request."""
    return request.args.get("user")
```
<details>
<summary><b>See HTTP Request</b></summary>

```shell
@base = http://localhost:8000/confusion/source-precedence

### Squidward can access his own messages as in example 2
POST {{base}}/example3?user=squidward
Content-Type: application/x-www-form-urlencoded

user=squidward&password=clarinet123

# [
#   {
#     "from": "mr.krabs",
#     "message": "Squidward, ..."
#   }, ...
# ]

### We are still sending the same username twice, I wonder if the attack still works...
POST {{base}}/example3?user=spongebob
Content-Type: application/x-www-form-urlencoded

user=squidward&password=clarinet123

# Nope, this time we get an unauthorized data access:
#   Invalid user or password

### Okay, placing victim's username into query string didn't work, but what if we put it into form body?
POST {{base}}/example3?user=squidward
Content-Type: application/x-www-form-urlencoded

user=spongebob&password=clarinet123

# [
#  {
#    "from": "patrick",
#    "message": "SpongeBob! I'm ready! I'm ready! Let's go jellyfishing!"
#  }
#]
```

</details>

### Example 4: Cross-Module Parameter Source Confusion <a id="ex-4"></a>

Confusion becomes even harder to detect when business logic splits across modules. The auth module uses form-based credentials (secure on its own) but doesn't match `messages_get` receiving a query string parameter.

Each file looks reasonable in isolation—authentication in `auth.py` follows best practices, route handlers in `routes.py` use standard query parameters. The vulnerability lives at the boundary between modules, where reviewers rarely look.
```python
@bp.post("/users/me/messages")
def list_messages():
    """
    Retrieves messages for an authenticated user.

    Delegates authentication to a shared utility function while handling
    message retrieval directly in the endpoint.
    """
    if not authenticate_user():
        return "Invalid user or password", 401

    return messages_get(request.args.get("user"))

def authenticate_user():
    """
    Authenticates the current user using form body credentials.

    Designed for POST-based authentication flows where credentials are in the request body,
    following security best practices to keep passwords out of URL logs.
    """
    return authenticate(request.form.get("user"), request.form.get("password"))

def authenticate(user, password):
    """Validates user credentials against the database."""
    return password and password == db["passwords"].get(user)


def messages_get(user):
    """Retrieves all messages for the specified user."""
    messages = db["messages"].get(user, [])
    return {"mailbox": user, "messages": messages}
```
<details>
<summary><b>See HTTP Request</b></summary>

```shell
@base = http://localhost:8000/confusion/source-precedence/example4

### Plankton accesses his own messages and notices that the username is sent twice
POST {{base}}/users/me/messages?user=plankton
Content-Type: application/x-www-form-urlencoded

user=plankton&password=chumbucket

# Results in 200 OK:
#
# {
#   "mailbox": "plankton",
#   "messages": [
#     {
#       "from": "karen",
#       "message": "Plankton, your plan to hack the Krusty Krab is ready. I've set up the proxy server."
#     }
#   ]
# }

### What if we change one of the usernames to Squidward?
POST {{base}}/users/me/messages?user=squidward
Content-Type: application/x-www-form-urlencoded

user=plankton&password=chumbucket

# {
#   "mailbox": "squidward",
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
```

</details>

## Helper-Induced Mixing

Utility functions that merge sources (or hide precedence rules) create subtle inconsistencies developers rarely spot in review.

### Example 5: Truthy-OR Parameter Precedence <a id="ex-5"></a>

Demonstrates a subtle vulnerability in "flexible" parameter resolution. The auth function resolves credentials via flexible fallback logic. Meanwhile, message retrieval only checks query parameters.

This DELETE endpoint demonstrates message destruction rather than unauthorized reading—attackers can erase evidence or disrupt communications.
```python
@bp.delete("/users/me/messages")
def delete_messages():
    """
    Manages user messages with delete operations.

    POST /messages
    user=mr.krabs&password=money&index=0&count=1
    """
    if not authenticate_principal(request):
        return "Invalid user or password", 401

    user = str(request.form.get("user"))
    index = int(request.form.get("index", 0))
    count = int(request.form.get("count", 1))

    deleted_messages_count = messages_delete(user, index, count)
    return {"status": "deleted", "user": user, "index": index, "count": deleted_messages_count}

def _resolve(request, key):
    return request.args.get(key) or request.form.get(key)

def authenticate_principal(request):
    """Authenticates the current user with flexible parameter resolution."""
    principal = _resolve(request, "user")
    password = _resolve(request, "password")
    return authenticate(principal, password)
```
<details>
<summary><b>See HTTP Request</b></summary>

```shell
@base = http://localhost:8000/confusion/source-precedence/example5

### Squidward notified Mr. Krabs about Plankton doing something suspicious
### Mr. Krabs would see this if he went to the messages page:
GET {{base}}/users/me/messages?user=mr.krabs&password=money
# {
#   "mailbox": "mr.krabs",
#   "messages": [
#     {
#       "from": "squidward",
#       "message": "I saw Plankton buying a mechanical keyboard, he's planning to hack us!"
#     }
#   ]
# }

### But Plankton deletes Mr. Krabs' messages before Mr. Krabs can see them!
DELETE {{base}}/users/me/messages?user=plankton&password=chumbucket
Content-Type: application/x-www-form-urlencoded

user=mr.krabs&index=0&count=10
# {
#   "count": 1,
#   "index": 0,
#   "status": "deleted",
#   "user": "mr.krabs"
# }

### By the time Mr. Krabs refreshes the page the message is gone!
GET {{base}}/users/me/messages?user=mr.krabs&password=money
# {
#   "mailbox": "mr.krabs",
#   "messages": []
# }
```

</details>

### Example 6: dict.get() Default Parameter Precedence <a id="ex-6"></a>

The vulnerability shown in example 5 was fixed by reversing priority of parameters in the merge function `_resolve`. However, this introduces a new vulnerability in the message retrieval function.

Note that internet browsers and many web servers refuse body parameters for GET, however Flask does support them, opening an attack vector for the attacker.
```python
@bp.get("/users/me/messages")
def list_messages():
    """
    Retrieves messages for an authenticated user.

    GET /messages?user=mr.krabs&password=money
    """
    if not authenticate_principal(request):
        return "Invalid user or password", 401

    return messages_get(request.args.get("user"))

def _resolve(request, key):
    return request.form.get(key, request.args.get(key))


def authenticate_principal(request):
    """Authenticates the current user with flexible parameter resolution."""
    principal = _resolve(request, "user")
    password = _resolve(request, "password")
    return authenticate(principal, password)
```
<details>
<summary><b>See HTTP Request</b></summary>

```shell
@base = http://localhost:8000/confusion/source-precedence/example6

### Message API looks more secure this time, it's a GET request and the username is only sent once
GET {{base}}/users/me/messages?user=squidward&password=clarinet123
# {
#   "owner": "squidward",
#   "messages": [ ... ]
# }

### Generally, GET requests shouldn't have a body, but Flask doesn't prevent it and still parses request.form
### Here, Squidward remains able to access SpongeBob's messages:
GET {{base}}/users/me/messages?user=spongebob
Content-Type: application/x-www-form-urlencoded

user=squidward&password=clarinet123
# {
#   "owner": "spongebob",
#   "messages": [
#     {
#       "from": "patrick",
#       "message": "SpongeBob! I'm ready! I'm ready! Let's go jellyfishing!"
#     }
#   ]
# }
```

</details>

## request.values Footguns

`request.values` promises convenience but applies its own precedence rules, leading to silent bypasses when paired with explicit `.args` or `.form` lookups.

### Example 7: Flask's request.values Precedence Rules <a id="ex-7"></a>

This example is functionally equivalent to example 5, except here we use built-in `request.values` instead of writing our own source merging function.

Flask's `request.values` is a `CombinedMultiDict` merging `request.args` and `request.form` with **args taking precedence** when keys collide. This means `?user=attacker` in the URL overrides `user=victim` in the POST body.

This version of `authenticate_user` relies on `request.form` and is secure on its own, but the vulnerability arises when `get_messages` uses `request.values` instead.
```python
@bp.post("/users/me/messages")
def list_messages():
    """
    Retrieves messages for an authenticated user.

    Example request:
      POST /users/me/messages
      Content-Type: application/x-www-form-urlencoded

      user=mr.krabs&password=money
    """
    if not authenticate_user():
        return "Invalid user or password", 401

    return messages_get(request.values.get("user"))

def authenticate_user():
    """
    Authenticates the user using form-based credentials.

    Designed for POST-based form submissions where credentials are in the request body.
    """
    return authenticate(request.form.get("user"), request.form.get("password"))
```
<details>
<summary><b>See HTTP Request</b></summary>

```shell
@base = http://localhost:8000/confusion/source-precedence/example7

### Credentials are passed via form body only here (best practice to avoid logging them)
POST {{base}}/users/me/messages
Content-Type: application/x-www-form-urlencoded

user=squidward&password=clarinet123

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

### The endpoint is still vulnerable!
POST {{base}}/users/me/messages?user=spongebob
Content-Type: application/x-www-form-urlencoded

user=squidward&password=clarinet123

# {
#   "owner": "spongebob",
#   "messages": [
#     {
#       "from": "patrick",
#       "message": "SpongeBob! I'm ready! I'm ready! Let's go jellyfishing!"
#     }
#   ]
# }
```

</details>

### Example 8: Inconsistent request.values Adoption <a id="ex-8"></a>

Developers "fixed" the vulnerability in example 7, but introduced a NEW vulnerability when adding password update functionality.

Updated authentication function uses `request.values` to verify WHO is making the request, but the target user whose password gets updated comes from `request.form` only.
```python
@bp.patch("/users/me/password")
def change_password():
    """
    Updates a user's password.

    Example request:
      PATCH /users/me/password
      Content-Type: application/x-www-form-urlencoded

      user=mr.krabs&password=money&new_password=new_password
    """
    if not authenticate_user():
        return "Invalid user or password", 401

    target_user = request.form.get("user")
    new_password = request.form.get("new_password")

    if not target_user or not new_password:
        return "Missing required parameters", 400

    if password_update(target_user, new_password):
        return {"status": "success", "user": target_user, "message": "Password updated"}
    else:
        return "User not found", 404

def authenticate_user():
    """
    Authenticates the user using form-based credentials.

    Designed for POST-based form submissions where credentials are in the request body.
    """
    return authenticate(request.values.get("user"), request.values.get("password"))
```
<details>
<summary><b>See HTTP Request</b></summary>

```shell
@base = http://localhost:8000/confusion/source-precedence/example8

### Plankton investigates password reset endpoint
PATCH {{base}}/users/me/password
Content-Type: application/x-www-form-urlencoded

user=plankton&password=chumbucket&new_password=bestburgersintown

# Results in successful password change:
# {
#   "status": "success",
#   "user": "plankton",
#   "message": "Password updated"
# }

### How about changing Mr. Krabs' password?
PATCH {{base}}/users/me/password?user=plankton
Content-Type: application/x-www-form-urlencoded

user=mr.krabs&password=bestburgersintown&new_password=pl4nkt0nd4b3st

# Results in successful password change:
# {
#   "status": "success",
#   "user": "mr.krabs",
#   "message": "Password updated"
# }

### Account takeover! Not just reading data anymore - Plankton now OWNS Mr. Krabs' account.
POST {{base}}/users/me/messages
Content-Type: application/x-www-form-urlencoded

user=mr.krabs&password=pl4nkt0nd4b3st
# {
#   "mailbox": "mr.krabs",
#   "messages": [
#     {
#       "from": "squidward",
#       "message": "I saw Plankton buying a mechanical keyboard, he's planning to hack us!"
#     }
#   ]
# }
```

</details>

