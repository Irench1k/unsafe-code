from flask import request

from .db import authenticate


# @unsafe[block]
# id: 7
# title: Form Authentication Bypass
# notes: |
#   The endpoint uses form data for authentication, but request.values.get() allows query parameters to override form values, creating a vulnerability. Although designed for POST requests, the endpoint accepts both GET and POST methods, enabling the attack.
#
#   Note that although the regular usage would rely on POST request (or PUT, PATCH, etc.), and wouldn't work with GET (because flask's request.values ignores form data in GET requests), the attacker can send both GET and POST requests (if the endpoint is configured to accept both methods).
#
#   ```http
#   POST /ii/source-precedence/example7? HTTP/1.1
#   Content-Type: application/x-www-form-urlencoded
#   Content-Length: 35
#
#   user=spongebob&password=bikinibottom
#   ```
#
#   However, the attacker can send both GET and POST requests (if the endpoint is configured to accept both methods).
# @/unsafe
def authenticate_user():
    """
    Authenticates the user using form-based credentials.

    Designed for POST-based form submissions where credentials are in the request body.
    """
    return authenticate(
        request.form.get("user", None), request.form.get("password", None)
    )


# @/unsafe[block]
