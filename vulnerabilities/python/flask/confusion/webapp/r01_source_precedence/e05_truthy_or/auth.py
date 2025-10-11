from .db import authenticate


# @unsafe[block]
# id: 5
# part: 2
# @/unsafe
def _resolve(request, key):
    return request.args.get(key) or request.form.get(key)

def authenticate_principal(request):
    """Authenticates the current user with flexible parameter resolution."""
    principal = _resolve(request, "user")
    password = _resolve(request, "password")
    return authenticate(principal, password)
# @/unsafe[block]
