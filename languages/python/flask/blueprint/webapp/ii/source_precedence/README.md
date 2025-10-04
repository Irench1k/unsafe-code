# Source Precedence Drift in Flask
When authentication trusts one request container and the handler trusts another, attackers can swap values between query strings, form bodies, JSON, or path params.
## Overview

Source precedence bugs creep in when two parts of the stack read the "same" input from different sources. Flask makes this easy: query strings, HTML form bodies, JSON payloads, and path parameters each land in different containers, and helpers like `request.values` silently merge them with their own priority rules.

**Common causes:** - Security code in decorators or helpers reads from `request.args` while the view trusts `request.form` or `request.get_json()`. - Refactors that move from query parameters to JSON do not update the guard. - Tests rarely cover both body and query variants, so the inconsistency remains hidden until production.

**Review checklist:** 1. Identify every lookup of the relevant key (e.g. `user`, `group`, `account_id`). 2. Note whether it comes from `.args`, `.form`, `.view_args`, `.json`, or `.values`. 3. Confirm the security decision and the business logic read from the same place, or explicitly reconcile them before use.

The examples below currently live in `confusion/parameter_source/` and will migrate here with the new taxonomy.

## Table of Contents

| Category | Example | File |
|:---:|:---:|:---:|
| Secure Baselines | [Example 0: Secure Implementation](#ex-0) | [routes.py](routes.py#L38-L54) |
| Straightforward Source Drift | [Example 1: Basic Parameter Source Confusion](#ex-1) | [routes.py](routes.py#L71-L85) |
| Straightforward Source Drift | [Example 2: Function-Level Parameter Source Confusion](#ex-2) | [routes.py](routes.py#L95-L119) |
| Straightforward Source Drift | [Example 3: Cross-Module Parameter Source Confusion](#ex-3) | [routes.py](routes.py#L135-L151) |
| Helper-Induced Mixing | [Example 4: Form-Query Priority Resolution](#ex-4) | [routes.py](routes.py#L165-L180) |
| Helper-Induced Mixing | [Example 5: Mixed-Source Authentication](#ex-5) | [routes.py](routes.py#L194-L209) |
| request.values Footguns | [Example 6: Form Authentication Bypass](#ex-6) | [routes.py](routes.py#L233-L250) |
| request.values Footguns | [Example 7: Request.Values in Authentication](#ex-7) | [routes.py](routes.py#L264-L277) |

## Secure Baselines
Consistent usage keeps authentication and data access aligned - use these to understand the intended flow before exploring the vulnerable variants.
<a id="ex-0"></a>

### Example 0: Secure Implementation
Here you can see a secure implementation that consistently uses query string parameters for both authentication and data retrieval.
```python
@bp.route("/example0", methods=["GET", "POST"])
def example0():
    # Extract the user name from the query string arguments
    user = request.args.get("user", None)

    # Validate the user name
    password = db["passwords"].get(user, None)
    if password is None or password != request.args.get("password", None):
        return "Invalid user or password", 401

    # Retrieve the messages for the user
    messages = db["messages"].get(user, None)
    if messages is None:
        return "No messages found", 404

    # return the messages
    return messages
```
<details open>
<summary><b>See HTTP Request</b></summary>

```http
GET http://localhost:8000/vuln/ii/source-precedence/example0?user=alice&password=123456
```
</details>

## Straightforward Source Drift
Simple handlers where the guard inspects query parameters but the action trusts form data or vice versa.
<a id="ex-1"></a>

### Example 1: Basic Parameter Source Confusion
Demonstrates the most basic form of parameter source confusion where authentication uses **query** parameters but data retrieval uses **form** data.

We take the user name from the query string during the validation, but during the data retrieval another value is used, taken from the request body (form). This does not look very realistic, but it demonstrates the core of the vulnerability, we will build upon this further.

Here you can see if we provide bob's name in the request body, we can access his messages without his password.
```python
@bp.route("/example1", methods=["GET", "POST"])
def example1():
    user = request.args.get("user", None)

    password = db["passwords"].get(user, None)
    if password is None or password != request.args.get("password", None):
        return "Invalid user or password", 401

    # Use the POST value which was not validated!
    user = request.form.get("user", None)
    messages = db["messages"].get(user, None)
    if messages is None:
        return "No messages found", 404

    return messages
```
<details>
<summary><b>See HTTP Request</b></summary>

```http
# Expected Usage:
GET http://localhost:8000/confusion/parameter-source/example1?user=alice&password=123456
Content-Type: application/x-www-form-urlencoded

user=alice
###

# Attack
GET http://localhost:8000/confusion/parameter-source/example1?user=alice&password=123456
Content-Type: application/x-www-form-urlencoded

user=bob
```

</details>

<a id="ex-2"></a>

### Example 2: Function-Level Parameter Source Confusion
Functionally equivalent to example 1, but shows how separating authentication and data retrieval into different functions can make the vulnerability harder to spot.
```python
def authenticate(user, password):
    if password is None or password != db["passwords"].get(user, None):
        return False
    return True


def get_messages(user):
    messages = db["messages"].get(user, None)
    if messages is None:
        return None
    return {"owner": user, "messages": messages}


@bp.route("/example2", methods=["GET", "POST"])
def example2():
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

```http
# Expected Usage:
GET http://localhost:8000/confusion/parameter-source/example2?user=alice&password=123456
Content-Type: application/x-www-form-urlencoded

user=alice
#
# Normally, Alice would get her *own* messages:
#
# [
#  {
#    "from": "kevin",
#    "message": "Hi Alice, you're fired!"
#  }
# ]
#
###

# Attack
GET http://localhost:8000/confusion/parameter-source/example2?user=alice&password=123456
Content-Type: application/x-www-form-urlencoded

user=bob
#
# Alice gets Bob's messages, even though she provided her own password!
#
# [
#  {
#    "from": "kevin",
#    "message": "Hi Bob, here is the password you asked for: P@ssw0rd!"
#  },
#  {
#    "from": "michael",
#    "message": "Hi Bob, come to my party on Friday! The secret passphrase is 'no-one-knows-it'!"
#  }
# ]
```
</details>

<a id="ex-3"></a>

### Example 3: Cross-Module Parameter Source Confusion
In the previous example, you can still see that the `user` value gets retrieved from the `request.args` during validation but from the `request.form` during data retrieval.

A more subtle example, where this is not immediately obvious (imagine, `authenticate_user` is defined in an another file altogether):
```python
def authenticate_user():
    """Authenticate the user, based solely on the request query string."""
    return authenticate(
        request.args.get("user", None), request.args.get("password", None)
    )


@bp.route("/example3", methods=["GET", "POST"])
def example3():
    if not authenticate_user():
        return "Invalid user or password", 401

    messages = get_messages(request.form.get("user", None))
    if messages is None:
        return "No messages found", 404

    return messages
```
<details>
<summary><b>See HTTP Request</b></summary>

```http
# Expected Usage:
GET http://localhost:8000/confusion/parameter-source/example3?user=alice&password=123456
Content-Type: application/x-www-form-urlencoded

user=alice
#
# Normally, Alice would get her *own* messages:
#
# [
#  {
#    "from": "kevin",
#    "message": "Hi Alice, you're fired!"
#  }
# ]
#
###

# Attack
GET http://localhost:8000/confusion/parameter-source/example3?user=alice&password=123456
Content-Type: application/x-www-form-urlencoded

user=bob
#
# Alice gets Bob's messages, even though she provided her own password!
#
# [
#  {
#    "from": "kevin",
#    "message": "Hi Bob, here is the password you asked for: P@ssw0rd!"
#  },
#  {
#    "from": "michael",
#    "message": "Hi Bob, come to my party on Friday! The secret passphrase is 'no-one-knows-it'!"
#  }
# ]
```

</details>

## Helper-Induced Mixing
Utility functions that merge sources (or hide precedence rules) create subtle inconsistencies developers rarely spot in review.
<a id="ex-4"></a>

### Example 4: Form-Query Priority Resolution
Shows how a helper function that implements source prioritization can create vulnerabilities.

In Example 4 we don't need to specify body parameters to get a result (which is now more realistic!), but if we want, we can still access bob's messages by passing his user name in the request body:
```python
def get_user():
    user_from_form = request.form.get("user", None)
    user_from_args = request.args.get("user", None)

    return user_from_form or user_from_args


@bp.route("/example4", methods=["GET", "POST"])
def example4():
    if not authenticate_user():
        return "Invalid user or password", 401

    messages = get_messages(get_user())
    if messages is None:
        return "No messages found", 404
    return messages
```
<details>
<summary><b>See HTTP Request</b></summary>

```http
# Expected Usage:
GET http://localhost:8000/confusion/parameter-source/example4?user=alice&password=123456
Content-Type: application/x-www-form-urlencoded

user=alice
#
# Normally, Alice would get her *own* messages:
#
# [
#  {
#    "from": "kevin",
#    "message": "Hi Alice, you're fired!"
#  }
# ]
#
###

# Attack
GET http://localhost:8000/confusion/parameter-source/example4?user=alice&password=123456
Content-Type: application/x-www-form-urlencoded

user=bob
#
# Alice gets Bob's messages, even though she provided her own password!
#
# [
#  {
#    "from": "kevin",
#    "message": "Hi Bob, here is the password you asked for: P@ssw0rd!"
#  },
#  {
#    "from": "michael",
#    "message": "Hi Bob, come to my party on Friday! The secret passphrase is 'no-one-knows-it'!"
#  }
# ]
```

</details>

<a id="ex-5"></a>

### Example 5: Mixed-Source Authentication
Shows how authentication and data access can use different combinations of sources.

This one is interesting, because you can access Bob's messages by providing his username and Alice's password in the request query, while providing Alice's username in the request body:
```python
def authenticate_user_example5():
    """Authenticate the user, based solely on the request query string."""
    user = get_user()
    password = request.args.get("password", None)
    return authenticate(user, password)


@bp.route("/example5", methods=["GET", "POST"])
def example5():
    if not authenticate_user_example5():
        return "Invalid user or password", 401

    messages = get_messages(request.args.get("user", None))
    if messages is None:
        return "No messages found", 404
    return messages
```
<details>
<summary><b>See HTTP Request</b></summary>

```http
# Expected Usage:
GET http://localhost:8000/confusion/parameter-source/example5?user=alice&password=123456
Content-Type: application/x-www-form-urlencoded

user=alice
#
# Normally, Alice would get her *own* messages:
#
# [
#  {
#    "from": "kevin",
#    "message": "Hi Alice, you're fired!"
#  }
# ]
#
###

# Attack
GET http://localhost:8000/confusion/parameter-source/example5?user=bob&password=123456
Content-Type: application/x-www-form-urlencoded

user=alice
#
# Alice gets Bob's messages, even though she provided her own password!
#
# [
#  {
#    "from": "kevin",
#    "message": "Hi Bob, here is the password you asked for: P@ssw0rd!"
#  },
#  {
#    "from": "michael",
#    "message": "Hi Bob, come to my party on Friday! The secret passphrase is 'no-one-knows-it'!"
#  }
# ]
```

</details>

## request.values Footguns
`request.values` promises convenience but applies its own precedence rules, leading to silent bypasses when paired with explicit `.args` or `.form` lookups.
<a id="ex-6"></a>

### Example 6: Form Authentication Bypass
The endpoint uses form data for authentication, but request.values.get() allows query parameters to override form values, creating a vulnerability. Although designed for POST requests, the endpoint accepts both GET and POST methods, enabling the attack.

Note that although the regular usage would rely on POST request (or PUT, PATCH, etc.), and wouldn't work with GET (because flask's request.values ignores form data in GET requests), the attacker can send both GET and POST requests (if the endpoint is configured to accept both methods).

```http
POST /ii/source-precedence/example6? HTTP/1.1
Content-Type: application/x-www-form-urlencoded
Content-Length: 26

user=alice&password=123456
```

However, the attacker can send both GET and POST requests (if the endpoint is configured to accept both methods).
```python
def authenticate_user_example6():
    """Authenticate the user, based solely on the request body."""
    return authenticate(
        request.form.get("user", None), request.form.get("password", None)
    )


@bp.route("/example6", methods=["GET", "POST"])
def example6():
    if not authenticate_user_example6():
        return "Invalid user or password", 401

    # The vulnerability occurs because flask's request.values merges the form and query string
    messages = get_messages(request.values.get("user", None))
    if messages is None:
        return "No messages found", 404

    return messages
```
<details>
<summary><b>See HTTP Request</b></summary>

```http
# Regular requests would pass credentials solely via POST body:
POST http://localhost:8000/confusion/parameter-source/example6
Content-Type: application/x-www-form-urlencoded

user=alice&password=123456

# And as usual, Alice would get her *own* messages:
#
# [
#  {
#    "from": "kevin",
#    "message": "Hi Alice, you're fired!"
#  }
# ]
#

###

# Attacker can get Alice's messages by adding user=alice to the query string:
POST http://localhost:8000/confusion/parameter-source/example6?user=bob
Content-Type: application/x-www-form-urlencoded

user=alice&password=123456
###

# Notably, attack works even with the GET request, assuming it's enabled:
GET http://localhost:8000/confusion/parameter-source/example6?user=bob
Content-Type: application/x-www-form-urlencoded

user=alice&password=123456

# Alice gets Bob's messages, even though she provided her own password!
#
# [
#  {
#    "from": "kevin",
#    "message": "Hi Bob, here is the password you asked for: P@ssw0rd!"
#  },
#  {
#    "from": "michael",
#    "message": "Hi Bob, come to my party on Friday! The secret passphrase is 'no-one-knows-it'!"
#  }
# ]
```

</details>

<a id="ex-7"></a>

### Example 7: Request.Values in Authentication
Demonstrates how using request.values in authentication while using form data for access creates vulnerabilities.

This is an example of a varient of example 6, as we do the similar thing, but now we can pass Bob's username in the request body with Alice's password, while passing Alice's username in the request query. Note that this example does not work with GET request, use POST.
```python
@bp.route("/example7", methods=["GET", "POST"])
def example7():
    # Authenticate using merged values
    if not authenticate(
        request.values.get("user", None), request.values.get("password", None)
    ):
        return "Invalid user or password", 401

    # But retrieve messages using only form data
    messages = get_messages(request.form.get("user", None))
    if messages is None:
        return "No messages found", 404

    return messages
```
<details>
<summary><b>See HTTP Request</b></summary>

```http
# Regular requests would pass credentials solely via POST body:
POST http://localhost:8000/confusion/parameter-source/example7
Content-Type: application/x-www-form-urlencoded

user=alice&password=123456

# And as usual, Alice would get her *own* messages:
#
# [
#  {
#    "from": "kevin",
#    "message": "Hi Alice, you're fired!"
#  }
# ]
#

###

# Attacker can get Alice's messages by adding user=alice to the query string:
POST http://localhost:8000/confusion/parameter-source/example7?user=alice
Content-Type: application/x-www-form-urlencoded

user=bob&password=123456
```

</details>

