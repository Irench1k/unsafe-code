from ..db import db


def authenticate(user, password):
    """Validates user credentials against the database."""
    return password and password == db["passwords"].get(user)
