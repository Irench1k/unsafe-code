from functools import wraps
from .database import authenticate


# @unsafe[block]
# id: 8
# part: 2
# @/unsafe
def authentication_required(f):
    @wraps(f)
    def decorated_example8(*args, **kwargs):
        if not authenticate():
            return "Invalid user or password", 401
        return f(*args, **kwargs)

    return decorated_example8


# @/unsafe[block]
