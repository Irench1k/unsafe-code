import logging
from hmac import compare_digest

from flask import g, request, session

from ..database.repository import get_restaurant_api_key
from ..database.services import get_current_user

logger = logging.getLogger(__name__)


class CustomerAuthenticator:
    """
    The session-based customer authenticator for the web app.

    This authenticator handles cookie-based sessions created during login.
    It's the primary authentication method for web browser users.

    Request Context:
      - g.auth_context: Set to 'customer' during detection
      - g.customer_request: Set to True for rate limiting
      - g.authenticated_customer: Set to True if authentication succeeds
      - g.email, g.user, g.name, g.balance: Set only after validation
    """

    def __init__(self):
        self.email = session.get("email")
        if self.email:
            g.auth_context = "customer"
            g.customer_request = True
            logger.debug(f"Customer authenticated via session: {self.email}")

    def authenticate(self) -> bool:
        if not self.email:
            return False

        user = get_current_user(self.email)
        if not user:
            logger.warning(f"Session found for non-existent user: {self.email}")
            return False

        g.authenticated_customer = True
        g.email = self.email
        g.user = user
        g.name = user.name
        g.balance = user.balance

        logger.debug(f"Customer authenticated via session: {self.email}")
        return True


class CredentialAuthenticator:
    """Authenticates customers using email/password credentials.

    Supports both Basic Auth (for mobile app) and form/JSON login (for website).
    Unlike session-based auth, this verifies password on each request.
    """

    def __init__(self, email: str | None, password: str | None):
        self.email = email
        self.password = password

        if email and password:
            g.auth_context = "customer"
            g.customer_request = True
            logger.debug(f"Customer authenticated via credentials: {self.email}")

    def authenticate(self) -> bool:
        # Unlike the new session based authn, here we need to verify password each time
        if not self.email or not self.password:
            return False

        user = get_current_user(self.email)
        if not user:
            logger.warning(f"Authentication attempt for non-existent user: {self.email}")
            return False

        if not compare_digest(self.password, user.password):
            logger.warning(f"Invalid password for user: {self.email}")
            return False

        g.authenticated_customer = True
        g.email = self.email
        g.user = user
        g.name = user.name
        g.balance = user.balance

        logger.debug(f"Customer authenticated via credentials: {self.email}")
        return True

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


class APIKeyAuthenticator:
    """
    API key-based authenticator for restaurant managers.

    This authenticator checks X-API-Key header and validates it against the
    restaurant's genuine API key.
    """

    HEADER_NAME: str

    def __init__(self):
        self.api_key = request.headers.get(self.HEADER_NAME)
        if self.api_key:
            g.auth_context = "manager"
            g.manager_request = True

            logger.debug("Restaurant API key detected, attempting authentication...")

    def authenticate(self) -> bool:
        """Validates the api key."""
        if not self.api_key:
            return False

        correct_key = get_restaurant_api_key()
        is_valid = compare_digest(self.api_key, correct_key)

        if not is_valid:
            logger.warning("Invalid restaurant API key attempt")
            return False

        g.authenticated_manager = True
        logger.info("Restaurant API key authentication successful")
        return True


class RestaurantAuthenticator(APIKeyAuthenticator):
    """Authenticates restaurant managers using the restaurant's API key."""

    HEADER_NAME = "X-API-Key"


class PlatformAuthenticator(APIKeyAuthenticator):
    """Authenticates platform admins using the platform's API key."""

    HEADER_NAME = "X-Admin-API-Key"
