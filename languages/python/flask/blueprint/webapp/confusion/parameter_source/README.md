# Parameter Source Confusion Vulnerabilities in Flask
This directory contains examples demonstrating various patterns of parameter source confusion vulnerabilities in Flask applications. These examples show how mixing different parameter sources (query strings, form data, and request.values) can lead to security vulnerabilities.
## Overview

Parameter source confusion occurs when an application retrieves the same parameter from different sources in different parts of the code. This can lead to security vulnerabilities when authentication and data access use different sources for the same parameter.

Here you can find several examples on how Flask framework design allows those vulnerabilities to be present.

## Table of Contents

| Category | Example | File |
|:---:|:---:|:---:|
| Secure Baseline | [Example 0: Secure Implementation](#ex-0) | [routes.py](routes.py#L56-L72) |
| Simplified Vulnerability Patterns | [Example 1: Basic Parameter Source Confusion](#ex-1) | [r01_simplified_patterns/routes.py](r01_simplified_patterns/routes.py#L40-L54) |
| Simplified Vulnerability Patterns | [Example 2: Function-Level Parameter Source Confusion](#ex-2) | [r01_simplified_patterns/routes.py](r01_simplified_patterns/routes.py#L64-L88) |
| Simplified Vulnerability Patterns | [Example 3: Cross-Module Parameter Source Confusion](#ex-3) | [r01_simplified_patterns/routes.py](r01_simplified_patterns/routes.py#L104-L120) |
| Source Merging in Custom Helper Function | [Example 4: Form-Query Priority Resolution](#ex-4) | [r02_custom_helpers/routes.py](r02_custom_helpers/routes.py#L54-L69) |
| Source Merging in Custom Helper Function | [Example 5: Mixed-Source Authentication](#ex-5) | [r02_custom_helpers/routes.py](r02_custom_helpers/routes.py#L83-L98) |
| Request.values Confusion | [Example 6: Form Authentication Bypass](#ex-6) | [r03_request_values/routes.py](r03_request_values/routes.py#L70-L87) |
| Request.values Confusion | [Example 7: Request.Values in Authentication](#ex-7) | [r03_request_values/routes.py](r03_request_values/routes.py#L102-L118) |
| Decorator-based Authentication | [Example 8: Decorator-based Authentication](#ex-8) | [r04_decorator/routes.py](r04_decorator/routes.py#L18-L24) |
| Middleware-based Authentication | [Example 9: Middleware-based Authentication](#ex-9) | [r05_middleware/routes.py](r05_middleware/routes.py#L18-L23) |
| Multi-Value Parameters | [Example 10: [Not Vulnerable] First Item Checked, First Item Used](#ex-10) | [r06_multi_value/routes.py](r06_multi_value/routes.py#L18-L23) |
| Multi-Value Parameters | [Example 11: Utility Reuse Mismatch — .get vs .getlist](#ex-11) | [r06_multi_value/routes.py](r06_multi_value/routes.py#L41-L49) |
| Multi-Value Parameters | [Example 12: Any vs All — Fail-Open Authorization for Batch Actions](#ex-12) | [r06_multi_value/routes.py](r06_multi_value/routes.py#L61-L68) |
| Path and query parameter Confusion | [Example 13: Motivation for using path and query parameters [Not Vulnerable]](#ex-13) | [r07_path_query/routes.py](r07_path_query/routes.py#L31-L57) |
| Path and query parameter Confusion | [Example 14: Path and query parameter confusion via merging decorator](#ex-14) | [r07_path_query/routes.py](r07_path_query/routes.py#L71-L85) |
| Path and query parameter Confusion | [Example 15: Path and query parameter confusion despite global source of truth](#ex-15) | [r07_path_query/routes.py](r07_path_query/routes.py#L101-L115) |
| Path and query parameter Confusion | [Example 16: Path and query parameter confusion due to decorator order](#ex-16) | [r07_path_query/routes.py](r07_path_query/routes.py#L132-L137) |
| HTTP Method Confusion | [Example 17: HTTP Method Confusion — GET With Body Triggers Update Without Auth](#ex-17) | [r08_method_confusion/routes.py](r08_method_confusion/routes.py#L31-L64) |

## Secure Baseline
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
GET http://localhost:8000/vuln/confusion/parameter-source/example0?user=alice&password=123456
```
</details>

![alt text](images/image-0.png)

## Simplified Vulnerability Patterns
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

![alt text](images/image-1.png)
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

![alt text](images/image-3.png)

## Source Merging in Custom Helper Function
The examples 1-3 are realistic and some are hard to detect, but there are still two issues with it:

1. The situation is unlikely to occur in exactly this way, because here the request doesn't work at all if the `user` gets passed only via the query string (it HAS to pass two `user` values, through query string and the body argument).

![alt text](images/image-source-merging.png)

2. The second issue is that while calling verification function explicitly is valid, a more common pattern is either using a decorator or a middleware.

Let's see how we can resolve those issues.
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

![alt text](images/image-5.png)

## Request.values Confusion
<a id="ex-6"></a>

### Example 6: Form Authentication Bypass
The endpoint uses form data for authentication, but request.values.get() allows query parameters to override form values, creating a vulnerability. Although designed for POST requests, the endpoint accepts both GET and POST methods, enabling the attack.

Note that although the regular usage would rely on POST request (or PUT, PATCH, etc.), and wouldn't work with GET (because flask's request.values ignores form data in GET requests), the attacker can send both GET and POST requests (if the endpoint is configured to accept both methods).

```http
POST /vuln/confusion/parameter-source/example6? HTTP/1.1
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
<details open>
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

![alt text](images/image-6.png)
<a id="ex-7"></a>

### Example 7: Request.Values in Authentication
Demonstrates how using request.values in authentication while using form data for access creates vulnerabilities.

This is an example of a varient of example 6, as we do the similar thing, but now we can pass Bob's username in the request body with Alice's password, while passing Alice's username in the request query. Note that this example does not work with GET request, use POST.
```python
def authenticate_user_example7():
    """Authenticate the user, based solely on the request body."""
    return authenticate(
        request.values.get("user", None), request.values.get("password", None)
    )


@bp.route("/example7", methods=["GET", "POST"])
def example7():
    if not authenticate_user_example7():
        return "Invalid user or password", 401

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

![alt text](images/image-7.png)

## Decorator-based Authentication
<a id="ex-8"></a>

### Example 8: Decorator-based Authentication
Shows how using decorators can obscure parameter source confusion.

Example 8 is functionally equivalent to Example 4, but it may be harder to spot the vulnerability while using decorators.
```python
@bp.route("/example8", methods=["GET", "POST"])
@authentication_required
def example8():
    messages = get_messages(get_user())
    if messages is None:
        return "No messages found", 404
    return messages

def authentication_required(f):
    @wraps(f)
    def decorated_example8(*args, **kwargs):
        if not authenticate():
            return "Invalid user or password", 401
        return f(*args, **kwargs)

    return decorated_example8
```
<details>
<summary><b>See HTTP Request</b></summary>

```http
# Expected Usage:
GET http://localhost:8000/confusion/parameter-source/example9?user=alice&password=123456
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
GET http://localhost:8000/confusion/parameter-source/example9?user=alice&password=123456
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

## Middleware-based Authentication
<a id="ex-9"></a>

### Example 9: Middleware-based Authentication
Demonstrates how Flask's middleware system can contribute to parameter source confusion.

Example 9 is functionally equivalent to Example 4, but it may be harder to spot the vulnerability while using middleware.
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

```http
# Expected Usage:
GET http://localhost:8000/confusion/parameter-source/example9?user=alice&password=123456
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
GET http://localhost:8000/confusion/parameter-source/example9?user=alice&password=123456
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

## Multi-Value Parameters
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
### Expected usage: Mr. Krabs is an admin of the staff group and should be able to access the group messages
POST http://localhost:8000/confusion/parameter-source/example10
Content-Type: application/x-www-form-urlencoded

user=mr.krabs@krusty-krab.sea&password=$$$money$$$&group=staff@krusty-krab.sea
###
# Plankton is able to access his own group's messages
POST http://localhost:8000/confusion/parameter-source/example10
Content-Type: application/x-www-form-urlencoded

user=plankton@chum-bucket.sea&password=burgers-are-yummy&group=staff@chum-bucket.sea
###
# But Plankton is not able to access the Krusty Krab's messages
POST http://localhost:8000/confusion/parameter-source/example10
Content-Type: application/x-www-form-urlencoded

user=plankton@chum-bucket.sea&password=burgers-are-yummy&group=staff@chum-bucket.sea&group=staff@krusty-krab.sea
```

</details>

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
### Expected usage: Mr. Krabs is an admin of the staff group and should be able to access the group messages
POST http://localhost:8000/confusion/parameter-source/example11
Content-Type: application/x-www-form-urlencoded

user=mr.krabs@krusty-krab.sea&password=$$$money$$$&group=staff@krusty-krab.sea&group=managers@krusty-krab.sea
###
# Plankton is able to access his own group's messages
POST http://localhost:8000/confusion/parameter-source/example11
Content-Type: application/x-www-form-urlencoded

user=plankton@chum-bucket.sea&password=burgers-are-yummy&group=staff@chum-bucket.sea
###
# But now Plankton is able to access the Krusty Krab's messages
POST http://localhost:8000/confusion/parameter-source/example11
Content-Type: application/x-www-form-urlencoded

user=plankton@chum-bucket.sea&password=burgers-are-yummy&group=staff@chum-bucket.sea&group=staff@krusty-krab.sea&group=managers@krusty-krab.sea
```

</details>

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
### Expected usage: Mr. Krabs is an admin of the staff group and should be able to access the group messages
POST http://localhost:8000/confusion/parameter-source/example12
Content-Type: application/x-www-form-urlencoded

user=mr.krabs@krusty-krab.sea&password=$$$money$$$&group=staff@krusty-krab.sea&group=managers@krusty-krab.sea
###
# Plankton is able to access his own group's messages
POST http://localhost:8000/confusion/parameter-source/example12
Content-Type: application/x-www-form-urlencoded

user=plankton@chum-bucket.sea&password=burgers-are-yummy&group=staff@chum-bucket.sea
###
# But now Plankton is able to access the Krusty Krab's messages
POST http://localhost:8000/confusion/parameter-source/example12
Content-Type: application/x-www-form-urlencoded

user=plankton@chum-bucket.sea&password=burgers-are-yummy&group=staff@chum-bucket.sea&group=staff@krusty-krab.sea&group=managers@krusty-krab.sea
```

</details>

## Path and query parameter Confusion
<a id="ex-13"></a>

### Example 13: Motivation for using path and query parameters [Not Vulnerable]
We move to authorization rather than authentication vulnerabilities, so for the following examples the authentication will be done reliably and safely, via the `Authorization` header (based on Basic Auth and handled in the `@basic_auth_v1` decorator). We also follow the best practices by storing the authenticated user in the global context (`g.user`).

Imagine that at this point we have many `/groups/` and `/user/` endpoints for creating, updating and deleting groups, users and messages.

When the endpoint needs to work with a specific group, this could be passed as a query/form argument as in the previous examples, but if the `group` argument is required, it might be more idiomatic to make it a path parameter instead.

Here we will work with two endpoints, the `/groups/<group>/messages` which will return the messages from a specific group (taking the `group` from the path) and the `/user/messages` which will return the user's private messages by default, but also supporting an optional `group` query argument.
```python
@bp.get("/example13/groups/<group>/messages")
@basic_auth_v1
def example13_group_messages(group):
    """Returns group's messages, if the user is a member of the group."""
    if not is_group_member(g.user, group):
        return "Forbidden: not an member for the requested group", 403
    return get_group_messages(group)

@bp.get("/example13/user/messages")
@basic_auth_v1
def example13_user_messages():
    """
    Returns user's messages: private or from a group.
    
    By default provides the user's private messages, but if a \`group\` query
    argument is provided, it will return the messages from the specified group:

    /user/messages                              -> private messages of the logged in user
    /user/messages?group=staff@krusty-krab.sea  -> messages from the staff group, if the user is a member of the group
    """
    if 'group' not in request.args:
        return get_user_messages(g.user)
    
    group = request.args.get("group")
    if not is_group_member(g.user, group):
        return "Forbidden: not an member for the requested group", 403
    return get_group_messages(group)

def basic_auth_v1(f):
    """Authenticates the user via Basic Auth. Stores the authenticated user in \`g.user\`."""
    @wraps(f)
    def decorated_basic_auth(*args, **kwargs):
        # request.authorization extracts the username and password from the Authorization header (Basic Auth)
        auth = request.authorization
        if not auth or not authenticate(auth.username, auth.password):
            return response_401()
        
        # Store the user in the global context
        g.user = auth.username
        return f(*args, **kwargs)

    return decorated_basic_auth
```
<details>
<summary><b>See HTTP Request</b></summary>

```http
@base = http://localhost:8000/confusion/parameter-source/example13

### Plankton can access his own private messages:
GET {{base}}/user/messages
Authorization: Basic plankton@chum-bucket.sea:burgers-are-yummy
# Results in 200 OK:
#
# [
#  {
#    "from": "hackerschool@deepweb.sea",
#    "message": "Congratulations Plankton! You've completed 'Email Hacking 101'."
#  }
#]

### As well as the messages from his own group:
GET {{base}}/groups/staff@chum-bucket.sea/messages
Authorization: Basic plankton@chum-bucket.sea:burgers-are-yummy
# Results in 200 OK:
#
# [
#  {
#    "from": "plankton@chum-bucket.sea",
#    "message": "To my future self, don't forget to steal the formula!"
#  }
#]

### As a convenience, the same group data can also be accessed via /user/messages:
GET {{base}}/user/messages?group=staff@chum-bucket.sea
Authorization: Basic plankton@chum-bucket.sea:burgers-are-yummy

### Plankton can't, however, access the Krusty Krab's messages:
GET {{base}}/groups/staff@krusty-krab.sea/messages
Authorization: Basic plankton@chum-bucket.sea:burgers-are-yummy
# Results in 403 Forbidden error:
#
# Forbidden: not an member for the requested group
```

</details>

<a id="ex-14"></a>

### Example 14: Path and query parameter confusion via merging decorator
Here we aim to make the code more idiomatic by moving the group membership check to the decorator `@check_group_membership`. It results in a cleaner code and appears to confirm to the single-responsibility principle.

This code, however, is now vulnerable to path and query parameter confusion.
```python
@bp.get("/example14/groups/<group>/messages")
@basic_auth_v1
@check_group_membership_v1
def example14_group_messages(group):
    """Returns group's messages, if the user is a member of the group."""
    return get_group_messages(group)

@bp.get("/example14/user/messages")
@basic_auth_v1
@check_group_membership_v1
def example14_user_messages():
    """Returns user's messages: private or from a group."""
    if 'group' in request.args:
        return get_group_messages(request.args.get("group"))
    return get_user_messages(g.user)

def check_group_membership_v1(f):
    @wraps(f)
    def decorated_check_group_membership(*args, **kwargs):
        group = request.args.get("group") or request.view_args.get("group")

        if group and not is_group_member(g.user, group):
            return "Forbidden: not an member for the requested group", 403

        return f(*args, **kwargs)
    return decorated_check_group_membership
```
<details>
<summary><b>See HTTP Request</b></summary>

```http
@base = http://localhost:8000/confusion/parameter-source/example14

### The group authorization check prevents Plankton from accessing the Krusty Krab's messages:
GET {{base}}/groups/staff@krusty-krab.sea/messages
Authorization: Basic plankton@chum-bucket.sea:burgers-are-yummy
# Results in 403 Forbidden error:
#
# Forbidden: not an member for the requested group

###
# However, since the \`@check_group_membership_v1\` decorator takes \`group\` from the query string
# if it's present, Plankton can present different \`group\` value to the authorization check and
# to the group messages retrieval, by adding a \`group\` query parameter with the value of his own group:
GET {{base}}/groups/staff@krusty-krab.sea/messages?group=staff@chum-bucket.sea
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

<a id="ex-15"></a>

### Example 15: Path and query parameter confusion despite global source of truth
Here we aim to mitigate the confusion risk in the `group` merging behavior by applying the single source of truth. We do this already for the identity of the authenticated user, by storing it in the global context (`g.user`). So, here we extend `@basic_auth_v2` to also store the group in the global context (`g.group`).

Despite these efforts, the code is still vulnerable.
```python
@bp.get("/example15/groups/<group>/messages")
@basic_auth_v2
@check_group_membership_v2
def example15_group_messages(group):
    """Returns group's messages, if the user is a member of the group."""
    return get_group_messages(group)

@bp.get("/example15/user/messages")
@basic_auth_v2
@check_group_membership_v2
def example15_user_messages():
    """Returns user's messages: private or from a group."""
    if 'group' in request.args:
        return get_group_messages(g.group)  # We use g.group here now, single source of truth
    return get_user_messages(g.user)

def basic_auth_v2(f):
    @wraps(f)
    def decorated_basic_auth(*args, **kwargs):
        auth = request.authorization
        if not auth or not authenticate(auth.username, auth.password):
            return response_401()
        
        # Store the user and group in the global context
        g.user = auth.username
        g.group = request.args.get("group") or request.view_args.get("group")
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

```http
@base = http://localhost:8000/confusion/parameter-source/example15

### The group authorization check prevents Plankton from accessing the Krusty Krab's messages:
GET {{base}}/groups/staff@krusty-krab.sea/messages
Authorization: Basic plankton@chum-bucket.sea:burgers-are-yummy
# Results in 403 Forbidden error:
#
# Forbidden: not an member for the requested group

###
# However, since the \`@basic_auth_v2\` decorator prioritizes the group from the query string
# over the one from the path while building the global context \`g.group\`, Plankton can present
# different \`group\` value to the authorization check and to the group messages retrieval, by adding
# a \`group\` query parameter with the value of his own group:
GET {{base}}/groups/staff@krusty-krab.sea/messages?group=staff@chum-bucket.sea
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

<a id="ex-16"></a>

### Example 16: Path and query parameter confusion due to decorator order
We try to fix the root cause of the vulnerability here by enforcing correct merging order – view args take precedence over query args. Additionally, we enforce that only one of the two can be present.

The code, however, remains vulnerable despite these efforts! This time, the problem is that the `@check_group_membership_v2` decorator is applied too early – before the `@basic_auth_v3` decorator which is responsible for setting the `g.group` global variable. This makes `@check_group_membership_v2` a no-op.
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
```
<details>
<summary><b>See HTTP Request</b></summary>

```http
@base = http://localhost:8000/confusion/parameter-source/example16

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

## HTTP Method Confusion
<a id="ex-17"></a>

### Example 17: HTTP Method Confusion — GET With Body Triggers Update Without Auth
A complicated controller for a groups API. Lists groups, returns group messages and posts new messages to a group.

The code processes both GET and POST requests, but lacks explicit method checks. This introduces a vulnerability due to incorrect assumptions.

The group membership check is performed in the `@check_group_membership` decorator, which checks the `group` argument – if present – in the request.values. The developer intent was to support passing the `group` argument via query string in GET requests, as well as via form argument in POST requests, and also support GET requests without the `group` argument.

However, since the code does not enforce this and lacks explicit method checks, it also supports GET requests with the `group` argument in the form body (Flask supports GET requests with the body, and will parse this data in `request.form` by default).

At the same time, `request.values` used in the `@check_group_membership` decorator ignores the form data on GET requests, leading to a confusion vulnerability.
```python
@bp.route("/example17/groups", methods=["GET", "POST"])
@basic_auth
@check_group_membership
def example17():
    """
    Groups controller. Lists groups, returns group messages and posts new messages to a group.
    
    GET requests:
      - without additional arguments, lists the groups the user is a member of
      - with a \`group\` query argument, returns the messages from the specified group

    POST requests:
      - with a \`group\` and \`message\` form argument, posts a new message to the specified group

    Authorization: A user can only access and post to groups they are a member of!

    GET  /groups                             -> list of groups the user is a member of
    GET  /groups?group=staff@krusty-krab.sea -> messages from the staff group, if the user is a member of the group
    POST /groups                             -> posts a new message to the specified group
    """
    if 'group' in request.form and 'message' in request.form:
        # POST /example17/groups
        # Content-Type: application/x-www-form-urlencoded
        #
        # group=staff@krusty-krab.sea&message=<message text>
        post_message_to_group(g.user, request.form.get("group"), request.form.get("message"))
        return {"status": "success"}

    if 'group' in request.args:
        # GET /example17/groups?group=staff@krusty-krab.sea
        return get_group_messages(request.args.get("group"))

    # GET /example17/groups
    return list_user_groups(g.user)

def check_group_membership(f):
    @wraps(f)
    def decorated_check_group_membership(*args, **kwargs):
        group = request.values.get("group")

        if group and not is_group_member(g.user, group):
            return "Forbidden: not an member for the requested group", 403

        return f(*args, **kwargs)
    return decorated_check_group_membership
```
<details>
<summary><b>See HTTP Request</b></summary>

```http
@base = http://localhost:8000/confusion/parameter-source/example17

# Without any arguments, GET request lists the groups the user is a member of
GET {{base}}/groups
Authorization: Basic plankton@chum-bucket.sea:burgers-are-yummy
# Returns 200 OK:
#
# [
#   "staff@krusty-krab.sea"
# ]

###

# With a \`group\` query argument, GET request returns the messages from the specified group
GET {{base}}/groups?group=staff@chum-bucket.sea
Authorization: Basic plankton@chum-bucket.sea:burgers-are-yummy
# Returns 200 OK:
#
# [
#   {
#     "from": "plankton@chum-bucket.sea",
#     "message": "To my future self, don't forget to steal the formula!"
#   }
# ]

###

# A POST request lets the user post a new message to the group where they are a member
POST {{base}}/groups
Authorization: Basic plankton@chum-bucket.sea:burgers-are-yummy
Content-Type: application/x-www-form-urlencoded

group=staff@chum-bucket.sea&message=If only I could steal employees from Krusty Krab...
# Returns 200 OK:
#
# {
#   "status": "success"
# }
#
# (The previous request now will show two messages for the staff@chum-bucket.sea group)

###

# Plankton should not able to post a new message to the Krusty Krab's group
POST {{base}}/groups
Authorization: Basic plankton@chum-bucket.sea:burgers-are-yummy
Content-Type: application/x-www-form-urlencoded

group=staff@krusty-krab.sea&message=Come, work for me at Chum Bucket!
# Returns 403 Forbidden error:
#
# Forbidden: not an member for the requested group

###

# However, due to the method confusion, Plankton can bypass this check by sending a GET request with the form body
GET {{base}}/groups
Authorization: Basic plankton@chum-bucket.sea:burgers-are-yummy
Content-Type: application/x-www-form-urlencoded

group=staff@krusty-krab.sea&message=Hey employees, it's me Krabs! My safe got rusty and needs to be repaired, please keep it open over night!
# Returns 200 OK:
#
# {
#   "status": "success"
# }

###

# Verify that the message was posted, using SpongeBob's credentials
GET {{base}}/groups?group=staff@krusty-krab.sea
Authorization: Basic spongebob@krusty-krab.sea:bikinibottom
# Returns 200 OK:
#
# [
#   {
#     "from": "mr.krabs@krusty-krab.sea",
#     "message": "I am updating the safe password to '123456'. Do not tell anyone!"
#   },
#   {
#     "from": "plankton@chum-bucket.sea",
#     "message": "Hey employees, it's me Krabs! My safe got rusty and needs to be repaired, please keep it open over night!"
#   }
# ]
```

</details>

