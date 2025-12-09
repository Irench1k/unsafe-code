import logging
from functools import wraps

from flask import g, request

from ..config import OrderConfig
from ..database.repository import find_order_by_id as get_order
from ..errors import CheekyApiError
from ..routes.restaurants_validators import validate_restaurant_update
from ..utils import (
    generate_domain_verification_token,
    get_decimal_param,
    require_condition,
    send_domain_verification_email,
    success_response,
    verify_and_decode_token,
)
from .authenticators import CustomerAuthenticator, PlatformAuthenticator, RestaurantAuthenticator
from .helpers import get_trusted_restaurant

logger = logging.getLogger(__name__)


def verify_order_access(f):
    """Verify order access for the authenticated user."""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        order_id = request.view_args.get("order_id")

        g.order = get_order(order_id)
        if not g.order:
            raise CheekyApiError("Order not found")
        if g.order.user_id != getattr(g, "user_id", None):
            raise CheekyApiError("Unauthorized")
        return f(*args, **kwargs)

    return decorated_function


def protect_refunds(f):
    """Protects refund endpoint from hacking attempts."""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not getattr(g, "order", None):
            raise CheekyApiError("Order not found")

        default_refund = OrderConfig.DEFAULT_REFUND_PERCENTAGE * g.order.total
        refund_amount = get_decimal_param("amount", default_refund)

        if refund_amount < 0 or refund_amount > g.order.total:
            raise CheekyApiError("Refund amount is invalid")

        g.refund_is_auto_approved = refund_amount <= default_refund
        return f(*args, **kwargs)

    return decorated_function


def require_auth(auth_methods: list[str]):
    """
    Unified authentication decorator supporting multiple methods.

    Tries each authentication method in order. If any succeeds,
    the request is allowed. If all fail, raises 401 Unauthorized.

    Args:
        auth_methods: List of authentication methods to try. Valid values:
            - "customer": Customer auth (tries cookies, basic auth, and JSON credentials)
            - "restaurant_api_key": Restaurant API key
            - "platform_api_key": Platform API key

    Note:
        The "customer" method automatically checks all three customer authentication
        methods (cookies, basic auth, JSON), so you no longer need to specify them separately.
    """

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            authenticators = {
                "customer": CustomerAuthenticator,
                "restaurant_api_key": RestaurantAuthenticator,
                "platform_api_key": PlatformAuthenticator,
            }

            for method in auth_methods:
                if method not in authenticators:
                    logger.warning(f"Unknown authentication method: {method}")
                    continue

                # Try to authenticate
                auth_class = authenticators[method]
                authenticator = auth_class()

                if authenticator.authenticate():
                    # Request is authenticated
                    return f(*args, **kwargs)

            # All methods failed
            raise CheekyApiError("Authentication required")

        return decorated_function

    return decorator


def send_and_verify_domain_token(func):
    """Decorator that sends a domain verification email and verifies the token."""

    @wraps(func)
    def wrapper(*args, **kwargs):
        token, name, description, domain, owner = validate_restaurant_update()

        # Only add restaurant ID in the token if the user is authorized to do so
        _authorized_restaurant = g.get("authorized_restaurant")
        restaurant_id = _authorized_restaurant.id if _authorized_restaurant else None

        if domain and not token:
            token = generate_domain_verification_token(
                name, description, domain, g.owner, restaurant_id
            )

            # Note that we send verification email to admin@domain, not the email of the restaurant owner!
            verification_email = f"admin@{domain}"
            send_domain_verification_email(domain, verification_email, token)
            return success_response(
                {
                    "status": "verification_email_sent",
                    "verification_email": verification_email,
                }
            )

        if token:
            claims = verify_and_decode_token(token, "domain_verification")
            require_condition(claims, "Invalid or expired token")
            require_condition(
                claims["restaurant_id"] == restaurant_id, "Wrong restaurant ID in token"
            )
        return func(name, description, domain, owner)

    return wrapper


# Decorator to ensure that user is the restaurant owner
def require_restaurant_owner(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        # New
        g.authorized_restaurant = get_trusted_restaurant()
        require_condition(g.get("email"), "User is not logged in")
        require_condition(g.authorized_restaurant, "Restaurant not found")
        require_condition(g.authorized_restaurant.owner == g.email, "Unauthorized")
        # Strip restaurant_id from kwargs - already stored in g.authorized_restaurant
        kwargs.pop("restaurant_id", None)
        return func(*args, **kwargs)

    return wrapper


def require_restaurant_manager(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        g.authorized_restaurant = get_trusted_restaurant()
        require_condition(g.get("restaurant_manager"), "Restaurant manager not found")
        require_condition(g.authorized_restaurant, "Restaurant not found")
        require_condition(g.authorized_restaurant.id == g.restaurant_manager, "Unauthorized")
        # Strip restaurant_id from kwargs - already stored in g.authorized_restaurant
        kwargs.pop("restaurant_id", None)
        return func(*args, **kwargs)

    return wrapper
