from hmac import compare_digest

from flask import request

from ..database.repository import get_api_key
from ..utils import verify_and_decode_token
from .authenticators import CredentialAuthenticator, CustomerAuthenticator


def authenticate_customer():
    """Try to authenticate customer using session-based or credential-based auth."""
    authenticator_from_cookie = CustomerAuthenticator()
    if authenticator_from_cookie.authenticate():
        return True

    authenticator_from_basic_auth = CredentialAuthenticator.from_basic_auth()
    return bool(authenticator_from_basic_auth.authenticate())


def _is_api_key_valid(api_key):
    """Validates the API key using the database."""
    if not api_key:
        return False

    correct_api_key = get_api_key()
    return compare_digest(api_key, correct_api_key)


def validate_api_key():
    """Validates the API key from the request."""
    api_key = request.headers.get("X-API-Key")
    if not api_key:
        return False

    return _is_api_key_valid(api_key)


def verify_user_registration(token: str) -> bool:
    """Check that the token is valid, and not expired, and does not belong to existing user."""
    decoded_token = verify_and_decode_token(token)
    if not decoded_token:
        return False

    email = decoded_token.get("email")
    if not email:
        print(f"The token was signed correctly, but there's no email! {token}")
        return False

    return True
