from decimal import Decimal
from functools import wraps

from flask import g, jsonify

from ..errors import CheekyApiError
from ..utils import get_request_parameter, parse_as_decimal
from .helpers import validate_api_key


def customer_authentication_required(f):
    """Authenticate customers via Basic Auth and authorize order access."""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not getattr(g, "email", None):
            raise CheekyApiError("User authentication required")
        return f(*args, **kwargs)

    return decorated_function


def verify_order_access(f):
    """Verify order access for the authenticated user."""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not getattr(g, "order", None) or g.order.user_id != g.email:
            raise CheekyApiError("Unathorized")
        return f(*args, **kwargs)

    return decorated_function


def restaurant_manager_authentication_required(f):
    """Authenticate restaurant managers via API key."""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not getattr(g, "is_restaurant_manager", None):
            raise CheekyApiError("Restaurant manager authentication required")
        return f(*args, **kwargs)

    return decorated_function


def protect_refunds(f):
    """Protects refund endpoint from hacking attempts."""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not getattr(g, "order", None):
            raise CheekyApiError("Order not found")

        _refund_requested = parse_as_decimal(get_request_parameter("amount"))
        refund_amount = _refund_requested or Decimal("0.2") * g.order.total

        if refund_amount < 0:
            raise CheekyApiError("Refund amount cannot be negative")

        if refund_amount > g.order.total:
            raise CheekyApiError("Refund amount cannot be greater than order total")

        g.refund_is_auto_approved = refund_amount <= Decimal("0.2") * g.order.total

        return f(*args, **kwargs)

    return decorated_function
