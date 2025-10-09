from .db import authenticate


# @unsafe[block]
# id: 5
# title: Mixed-Source Authentication
# notes: |
#   Shows how authentication and data access can use different combinations of sources.
#
#   This one is interesting, because you can access Squidward's messages by providing his username and SpongeBob's password in the request query, while providing SpongeBob's username in the request body:
# @/unsafe
def extract_principal(request):
    """
    Retrieves the user identifier from the request.

    Checks form data first for POST requests, falling back to query parameters
    to support both form submissions and direct URL access.
    """
    principal_from_form = request.form.get("user", None)
    principal_from_args = request.args.get("user", None)

    return principal_from_form or principal_from_args


def authenticate_principal(request):
    """
    Authenticates the current user with flexible parameter resolution.

    Uses the user resolution helper for username while taking password from query string.
    """
    principal = extract_principal(request)
    password = request.args.get("password", None)
    return authenticate(principal, password)


# @/unsafe[block]
