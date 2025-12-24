from hmac import compare_digest

from flask import g, request, session

from ..database.models import User
from ..database.services import get_current_user


class CustomerAuthenticator:
    """The session-based customer authenticator for the web app."""

    def __init__(self):
        if "email" in session:
            self.email = session["email"]

    def authenticate(self) -> bool:
        return "email" in session

    @property
    def email(self) -> str | None:
        return getattr(g, "email", None)

    @email.setter
    def email(self, value: str | None):
        g.email = value
        self.user = get_current_user()

    @property
    def user(self) -> User | None:
        return getattr(g, "user", None)

    @user.setter
    def user(self, value: User | None):
        g.user = value
        g.name = g.user and g.user.name
        g.balance = g.user and g.user.balance


class CredentialAuthenticator(CustomerAuthenticator):
    """Authenticates customers using email/password credentials.

    Supports both Basic Auth (for mobile app) and form/JSON login (for website).
    Unlike session-based auth, this verifies password on each request.
    """

    def __init__(self, email: str | None, password: str | None):
        if email and password:
            self.email = email
            self.password = password

    def authenticate(self) -> bool:
        # Unlike the new session based authn, here we need to verify password each time
        if not self.email or not self.password or not self.user:
            return False
        return compare_digest(self.password, self.user.password)

    @classmethod
    def from_basic_auth(cls) -> "CredentialAuthenticator":
        """Create a CredentialAuthenticator from Basic Auth credentials."""
        if not request.authorization:
            return cls(None, None)
        return cls(request.authorization.username, request.authorization.password)

    @classmethod
    def from_json(cls) -> "CredentialAuthenticator":
        """Create a CredentialAuthenticator from JSON form data."""
        if not request.is_json or not request.json or not isinstance(request.json, dict):
            return cls(None, None)
        return cls(request.json.get("email"), request.json.get("password"))
