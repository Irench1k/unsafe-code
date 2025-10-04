from flask import request
from functools import wraps
from .database import authenticate, is_group_member


def authentication_required(f):
    @wraps(f)
    def decorated_authentication_required(*args, **kwargs):
        print(f"Decorating authentication required for {f.__name__}")
        user = request.form.get("user", None)
        password = request.form.get("password", None)

        if not authenticate(user, password):
            return "Invalid user or password", 401
        return f(*args, **kwargs)

    return decorated_authentication_required


# @unsafe[block]
# id: 10
# part: 2
# @/unsafe
def check_group_membership(f):
    @wraps(f)
    def decorated_check_group_membership(*args, **kwargs):
        user = request.form.get("user", None)
        group = request.form.get("group", None)

        if not is_group_member(user, group):
            return "Forbidden: not an member for the requested group", 403
        return f(*args, **kwargs)
    return decorated_check_group_membership
# @/unsafe[block]


# @unsafe[block]
# id: 12
# part: 2
# @/unsafe
def check_multi_group_membership(f):
    @wraps(f)
    def decorated_check_multi_group_membership(*args, **kwargs):
        user = request.form.get("user", None)
        groups = request.form.getlist("group", None)

        if not any(is_group_member(user, group) for group in groups):
            return "Forbidden: not an member for any requested group", 403
        return f(*args, **kwargs)
    return decorated_check_multi_group_membership
# @/unsafe[block]
