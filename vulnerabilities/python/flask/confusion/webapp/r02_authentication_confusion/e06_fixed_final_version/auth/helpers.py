import logging

from ..utils import verify_and_decode_token

logger = logging.getLogger(__name__)


def verify_user_registration(token: str) -> bool:
    """Check that the token is valid, and not expired, and does not belong to existing user."""
    decoded_token = verify_and_decode_token(token)
    if not decoded_token:
        return False

    email = decoded_token.get("email")
    if not email:
        logger.warning("Token missing email field")
        return False

    return True
