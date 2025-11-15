from decimal import Decimal
from functools import wraps

from flask import g, request

from ..database.repository import find_order_by_id as get_order
from ..errors import CheekyApiError
from ..utils import get_request_parameter, parse_as_decimal
from .helpers import authenticate_customer, validate_api_key


def customer_authentication_required(f):
    """Authenticate customers via Basic Auth and authorize order access."""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not authenticate_customer():
            raise CheekyApiError("User authentication required")
        return f(*args, **kwargs)

    return decorated_function


def verify_order_access(f):
    """Verify order access for the authenticated user."""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        g.order = get_order(request.view_args.get("order_id"))
        if g.order and g.order.user_id != g.email:
            raise CheekyApiError("Unauthorized")
        return f(*args, **kwargs)

    return decorated_function


def restaurant_manager_authentication_required(f):
    """Authenticate restaurant managers via API key."""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not validate_api_key():
            raise CheekyApiError("Restaurant manager authentication required")
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
