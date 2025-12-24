import logging
from functools import wraps

from flask import g, request

from ..config import OrderConfig
from ..database.repository import find_order_by_id as get_order
from ..database.repository import find_resource_by_id
from ..errors import CheekyApiError
from ..utils import get_decimal_param
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

            # v304 fix: ALWAYS check that authenticated restaurant owns the resource
            # Previously only checked when restaurant_id was in the route path
            if resource.restaurant_id != g.restaurant_id:
                raise CheekyApiError(
                    f"{resource_class.__name__} {resource_id} does not belong to this restaurant"
                )

            # Optional: validate route restaurant_id matches (when present in path)
            requested_restaurant = values.get("restaurant_id")
            if requested_restaurant and requested_restaurant != g.restaurant_id:
                raise CheekyApiError("Unauthorized")

            return f(*args, **kwargs)

        return decorated_function

    return decorator
