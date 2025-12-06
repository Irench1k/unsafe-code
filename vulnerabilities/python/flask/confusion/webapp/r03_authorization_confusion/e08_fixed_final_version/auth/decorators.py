import logging
from functools import wraps

from flask import g, request

from ..config import OrderConfig
from ..database.repository import find_order_by_id as get_order
from ..database.repository import find_resource_by_id, find_restaurant_by_id
from ..errors import CheekyApiError
from ..utils import (
    generate_domain_verification_token,
    get_decimal_param,
    get_param,
    require_condition,
    send_domain_verification_email,
    success_response,
    verify_and_decode_token,
)
from .authenticators import CustomerAuthenticator, PlatformAuthenticator, RestaurantAuthenticator

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


def restaurant_owns(resource_class: type, resource_id_param: str):
    """
    Require that the authenticated restaurant owns the resource referenced in the route.

    Args:
        resource_class: SQLAlchemy model class that must expose a `restaurant_id` column.
        resource_id_param: Name of the route parameter identifying the resource (e.g., "item_id").
    """

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            values = request.view_args or {}
            resource_id = values.get(resource_id_param)

            resource = find_resource_by_id(resource_class, resource_id, resource_id_param)
            if resource is None:
                raise CheekyApiError(f"{resource_class.__name__} {resource_id} not found")

            requested_restaurant = values.get("restaurant_id")
            if requested_restaurant and requested_restaurant != resource.restaurant_id:
                raise CheekyApiError(
                    f"{resource_class.__name__} {resource_id} does not belong to this restaurant"
                )

            if requested_restaurant and requested_restaurant != g.restaurant_id:
                raise CheekyApiError("Unauthorized")

            return f(*args, **kwargs)

        return decorated_function

    return decorator


def send_and_verify_domain_token(func):
    """Decorator that sends a domain verification email and verifies the token."""

    @wraps(func)
    def wrapper(*args, **kwargs):
        token = get_param("token")
        name = get_param("name")
        description = get_param("description")
        domain = get_param("domain")
        owner = g.email
        restaurant_id = kwargs.get("restaurant_id")

        if domain and not token:
            token = generate_domain_verification_token(
                name, description, domain, owner, restaurant_id
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
            kwargs["verified_token"] = claims
        else:
            kwargs["verified_token"] = None
        return func(*args, **kwargs)

    return wrapper


# Decorator to ensure that user is the restaurant owner
def require_restaurant_owner(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        restaurant_id = kwargs.get("restaurant_id")
        restaurant = find_restaurant_by_id(restaurant_id)
        require_condition(restaurant, "Restaurant not found")
        require_condition(g.get("email"), "User is not logged in")
        require_condition(restaurant.owner == g.email, "Unauthorized")
        return func(*args, **kwargs)

    return wrapper
