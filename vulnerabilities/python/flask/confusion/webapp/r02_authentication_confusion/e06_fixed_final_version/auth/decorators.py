import logging
from decimal import Decimal
from functools import wraps

from flask import g, request

from ..database.repository import find_order_by_id as get_order
from ..errors import CheekyApiError
from ..utils import get_request_parameter, normalize_order_id, parse_as_decimal
from .authenticators import (
    CustomerAuthenticator,
    PlatformAuthenticator,
    RestaurantAuthenticator,
)

logger = logging.getLogger(__name__)


def verify_order_access(f):
    """Verify order access for the authenticated user."""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        view_args = request.view_args or {}
        order_id = normalize_order_id(view_args.get("order_id"))
        if not order_id:
            raise CheekyApiError("Invalid order ID")

        order = get_order(order_id)
        if not order:
            raise CheekyApiError("Order not found")

        if not getattr(g, "email", None):
            raise CheekyApiError("Authentication required")

        if order.user_id != g.email:
            raise CheekyApiError("Unauthorized")

        g.order = order
        return f(*args, **kwargs)

    return decorated_function


def protect_refunds(f):
    """Protects refund endpoint from hacking attempts."""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not getattr(g, "order", None):
            raise CheekyApiError("Order not found")

        default_refund = Decimal("0.2") * g.order.total
        refund_amount = parse_as_decimal(get_request_parameter("amount")) or default_refund

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
