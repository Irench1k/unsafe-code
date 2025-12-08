import logging
from hmac import compare_digest

from flask import g, request, session

from ..database.repository import (
    find_restaurant_by_api_key,
    get_platform_api_key,
)
from ..database.services import get_current_user

logger = logging.getLogger(__name__)


# ============================================================
# Base Authenticator
# ============================================================


class BaseAuthenticator:
    """Base class for all authenticators.

    All authenticators are stateless - they don't store request-specific data.
    Initialize once at app startup, then call authenticate() once per request.
    """

    def __init__(self):
        """Initialize authenticator. Should be empty - authenticators are stateless."""
        pass

    def authenticate(self) -> bool:
        """Authenticate the request.

        Returns:
            True if authentication succeeded, False otherwise.

        Side effects:
            Sets g.auth_context and other relevant flags/claims on success.
        """
        raise NotImplementedError

    def _set_standard_claims(self, auth_context: str, **flags) -> None:
        """Set standard claims shared by all authenticators.

        Args:
            auth_context: The authentication context (e.g., 'customer', 'manager', 'platform')
            **flags: Additional flags to set on g (e.g., customer_request=True)
        """
        g.auth_context = auth_context
        for flag_name, flag_value in flags.items():
            setattr(g, flag_name, flag_value)


# ============================================================
# Customer Authenticator
# ============================================================


class CustomerAuthenticator(BaseAuthenticator):
    """Authenticates customers via cookies, basic auth, or JSON credentials.

    This authenticator automatically tries all three customer authentication methods:
      1. Session cookies (web browser)
      2. HTTP Basic Auth (mobile app, API clients)
      3. Email/password in JSON body (REST API)

    Request Context (set only on successful authentication):
      - g.auth_context: 'customer'
      - g.customer_request: True (for rate limiting)
      - g.authenticated_customer: True
      - g.email, g.user_id, g.name, g.balance: Customer-specific claims
    """

    def authenticate(self) -> bool:
        """Try all customer authentication methods.

        Returns:
            True if any method succeeds, False if all fail.
        """
        # Try session-based auth first (most common for web app)
        if self._try_session_auth():
            return True

        # Try credential-based auth (basic auth or JSON)
        if self._try_credential_auth():
            return True

        logger.debug("No valid customer credentials found in request")
        return False

    def _try_session_auth(self) -> bool:
        """Try to authenticate via session cookie.

        Returns:
            True if session authentication succeeds, False otherwise.
        """
        email = session.get("email")
        if not email:
            return False

        user = get_current_user(email)
        if not user:
            logger.warning(f"Session found for non-existent user: {email}")
            return False

        self._authenticate_customer(email, user, auth_method="session")
        return True

    def _try_credential_auth(self) -> bool:
        """Try to authenticate via credentials (basic auth or JSON).

        Returns:
            True if credential authentication succeeds, False otherwise.
        """
        email, password = self._extract_credentials()

        if not email or not password:
            return False

        user = get_current_user(email)
        if not user:
            logger.warning(f"Credential authentication attempt for non-existent user: {email}")
            return False

        if not compare_digest(password, user.password):
            logger.warning(f"Invalid password for user: {email}")
            return False

        self._authenticate_customer(email, user, auth_method="credentials")
        return True

    def _authenticate_customer(self, email: str, user, auth_method: str) -> None:
        """Complete customer authentication by setting all required claims.

        Args:
            email: Customer email
            user: User object from database
            auth_method: Authentication method used (for logging)
        """
        self._set_standard_claims(
            "customer",
            customer_request=True,
            authenticated_customer=True,
        )
        self._set_customer_specific_claims(email, user)
        logger.debug(f"Customer authenticated via {auth_method}: {email}")

    def _extract_credentials(self) -> tuple[str | None, str | None]:
        """Extract credentials from basic auth or JSON.

        Returns:
            (email, password) tuple. Both are None if no credentials found.
        """
        # Try HTTP Basic Auth
        if request.authorization:
            username = request.authorization.username
            password = request.authorization.password
            # Basic auth must have both username and non-empty password
            if username and password:
                return username, password

        # Try JSON credentials
        if request.is_json and request.json and isinstance(request.json, dict):
            email = request.json.get("email")
            password = request.json.get("password")
            # JSON auth must have both email and password
            if email and password:
                return email, password

        return None, None

    def _set_customer_specific_claims(self, email: str, user) -> None:
        """Set customer-specific claims on g.

        These claims are only set for customer authentication,
        not for other authenticator types.
        """
        g.email = email
        g.user_id = user.id
        g.user = user
        g.name = user.name
        g.balance = user.balance


# ============================================================
# API Key Authenticators
# ============================================================


class APIKeyAuthenticator(BaseAuthenticator):
    """Base class for API key-based authentication.

    Subclasses must define:
      - HEADER_NAME: HTTP header to check for the API key
      - AUTH_CONTEXT: Authentication context name
      - REQUEST_FLAG: Flag name for request type (e.g., 'manager_request')
      - AUTHENTICATED_FLAG: Flag name for authentication status (e.g., 'authenticated_manager')

    Subclasses must implement:
      - _get_correct_key(): Return the correct API key for validation
    """

    HEADER_NAME: str
    AUTH_CONTEXT: str
    REQUEST_FLAG: str
    AUTHENTICATED_FLAG: str

    def authenticate(self) -> bool:
        """Authenticate via API key in HTTP header.

        Returns:
            True if API key is valid, False otherwise.
        """
        api_key = request.headers.get(self.HEADER_NAME)

        if not api_key:
            logger.debug(f"No {self.AUTH_CONTEXT} API key found in {self.HEADER_NAME} header")
            return False

        is_valid = self._is_valid_api_key(api_key)

        if not is_valid:
            logger.warning(f"Invalid {self.AUTH_CONTEXT} API key attempt")
            return False

        self._set_standard_claims(
            self.AUTH_CONTEXT,
            **{
                self.REQUEST_FLAG: True,
                self.AUTHENTICATED_FLAG: True,
            },
        )

        logger.info(f"{self.AUTH_CONTEXT.capitalize()} API key authentication successful")
        return True

    def _is_valid_api_key(self, api_key: str) -> bool:
        """Check if the API key is valid."""
        raise NotImplementedError


class RestaurantAuthenticator(APIKeyAuthenticator):
    """Authenticates restaurant managers using the restaurant's API key.

    Checks X-API-Key header and sets manager-related flags on g.
    """

    HEADER_NAME = "X-API-Key"
    AUTH_CONTEXT = "manager"
    REQUEST_FLAG = "manager_request"
    AUTHENTICATED_FLAG = "authenticated_manager"

    def _is_valid_api_key(self, api_key: str) -> bool:
        restaurant = find_restaurant_by_api_key(api_key)
        if restaurant is None:
            return False

        g.restaurant_id = restaurant.id
        return True


class PlatformAuthenticator(APIKeyAuthenticator):
    """Authenticates platform admins using the platform's API key.

    Checks X-Admin-API-Key header and sets platform-related flags on g.
    """

    HEADER_NAME = "X-Admin-API-Key"
    AUTH_CONTEXT = "platform"
    REQUEST_FLAG = "platform_request"
    AUTHENTICATED_FLAG = "authenticated_platform"

    def _is_valid_api_key(self, api_key: str) -> bool:
        return compare_digest(get_platform_api_key(), api_key)
