"""Restaurant Validators - Input validation and response serialization.

v405 Refactoring: All input access now uses the consume-once pattern from utils.py.
This ensures parameters can only be read once, preventing bugs where the same
parameter is accessed multiple times with potentially different values.

Validators in this file use consume_* helpers from utils.py. The consume pattern:
- For scalars: returns and removes the value
- For arrays: pops and returns the first element (supports batch operations)
- Returns None if already consumed or not present

This is a SECURITY IMPROVEMENT - ensures validated data can't be re-read
with different values later in the request lifecycle.
"""

from decimal import Decimal

from ..database.models import Coupon, MenuItem, Order, Refund, Restaurant, User
from ..errors import CheekyApiError
from ..utils import (
    consume_boolean,
    consume_decimal,
    consume_int_list,
    consume_param,
    consume_string,
    require_condition,
)


# ============================================================
# INPUT VALIDATION - MENU ITEMS
# ============================================================
def validate_menu_item_fields(
    *,
    require_name: bool = False,
    require_price: bool = False,
    require_any: bool = False,
) -> tuple[str | None, Decimal | None, bool | None]:
    """
    Validate and consume menu item fields from JSON body.

    Uses consume-once pattern: each field can only be read once.
    This prevents bugs where fields are read multiple times with
    potentially different values.
    """
    name = consume_string("name", required=require_name)
    price = consume_decimal("price", required=require_price, positive=True)
    available = consume_boolean("available")

    if require_any and not any([name, price, available is not None]):
        raise CheekyApiError("No fields provided")

    return name, price, available


# ============================================================
# INPUT VALIDATION - RESTAURANT REGISTRATION/UPDATE
# ============================================================
def validate_restaurant_update() -> tuple[dict | None, str | None, str | None, str | None, str | None]:
    """
    Parse and validate restaurant update from JSON body or verified token.

    Uses consume-once pattern for all field access.
    """
    # Token is a special case - it's a nested object, consume it whole
    token = consume_param("token")

    if token:
        if not isinstance(token, dict):
            raise CheekyApiError("token must be an object")
        name = token.get("name")
        description = token.get("description")
        domain = token.get("domain")
        owner = token.get("owner")
        require_condition(
            name and description and domain, "name, description and domain are required"
        )
    else:
        name = consume_string("name")
        description = consume_string("description")
        require_condition(name or description, "name or description is required")
        domain = None
        owner = None

    return token, name, description, domain, owner


# ============================================================
# INPUT VALIDATION - BATCH REFUND
# ============================================================
def validate_batch_refund_request() -> tuple[list[int], str]:
    """
    Validate batch refund request. Returns (order_ids, reason).

    Expects JSON: { "order_ids": [1, 2, 3], "reason": "Quality issue" }
    Uses consume-once pattern for all field access.
    """
    order_ids = consume_int_list("order_ids", required=True, min_length=1)
    reason = consume_string("reason") or "Batch refund initiated by restaurant"

    return order_ids, reason


# ============================================================
# RESPONSE SERIALIZATION - RESTAURANTS
# ============================================================
def serialize_restaurant(restaurant: Restaurant) -> dict:
    """Serialize a restaurant to JSON-compatible dict."""
    return {
        "id": restaurant.id,
        "name": restaurant.name,
        "description": restaurant.description,
        "domain": restaurant.domain,
    }


def serialize_restaurants(restaurants: list[Restaurant]) -> list[dict]:
    """Serialize a list of restaurants."""
    return [serialize_restaurant(r) for r in restaurants]


def serialize_restaurant_creation(restaurant: Restaurant) -> dict:
    """Serialize restaurant creation response (includes API key)."""
    return {
        "id": restaurant.id,
        "name": restaurant.name,
        "description": restaurant.description,
        "owner": restaurant.owner,
        "api_key": restaurant.api_key,
        "domain": restaurant.domain,
        "status": "created",
    }


# ============================================================
# RESPONSE SERIALIZATION - USERS
# ============================================================
def serialize_users(users: list[User]) -> list[dict]:
    """Serialize restaurant users."""
    return [{"email": user.email, "name": user.name} for user in users]


# ============================================================
# RESPONSE SERIALIZATION - MENU ITEMS
# ============================================================
def serialize_menu_item(menu_item: MenuItem) -> dict:
    """Serialize a single menu item."""
    return {
        "id": menu_item.id,
        "restaurant_id": menu_item.restaurant_id,
        "name": menu_item.name,
        "price": str(menu_item.price),
        "available": menu_item.available,
    }


def serialize_menu_items(menu_items: list[MenuItem]) -> list[dict]:
    """Serialize a list of menu items."""
    return [serialize_menu_item(item) for item in menu_items]


# ============================================================
# RESPONSE SERIALIZATION - COUPONS
# ============================================================
def serialize_coupon(coupon: Coupon) -> dict:
    """Serialize a coupon."""
    return {
        "id": coupon.id,
        "restaurant_id": coupon.restaurant_id,
        "code": coupon.code,
        "value": str(coupon.value) if coupon.value else None,
    }


def serialize_coupons(coupons: list[Coupon]) -> list[dict]:
    """Serialize a list of coupons."""
    return [serialize_coupon(c) for c in coupons]


# ============================================================
# RESPONSE SERIALIZATION - ORDERS
# ============================================================
def serialize_order(order: Order) -> dict:
    """Serialize an order."""
    return {
        "id": order.id,
        "restaurant_id": order.restaurant_id,
        "user_id": order.user_id,
        "total": str(order.total),
        "status": order.status.value,
        "created_at": order.created_at.isoformat() if order.created_at else None,
    }


def serialize_orders(orders: list[Order]) -> list[dict]:
    """Serialize a list of orders."""
    return [serialize_order(o) for o in orders]


# ============================================================
# RESPONSE SERIALIZATION - REFUNDS
# ============================================================
def serialize_refund(refund: Refund) -> dict:
    """Serialize a refund."""
    return {
        "id": refund.id,
        "order_id": refund.order_id,
        "amount": str(refund.amount),
        "reason": refund.reason,
        "status": refund.status.value,
        "auto_approved": refund.auto_approved,
        "created_at": refund.created_at.isoformat() if refund.created_at else None,
    }


def serialize_refunds(refunds: list[Refund]) -> list[dict]:
    """Serialize a list of refunds."""
    return [serialize_refund(r) for r in refunds]


def serialize_batch_refund_result(results: list[dict]) -> dict:
    """Serialize batch refund result from issue_order_refund results."""
    processed = [r["order_id"] for r in results if r["status"] == "processed"]
    skipped = [
        {"order_id": r["order_id"], "reason": r["reason"]}
        for r in results
        if r["status"] == "skipped"
    ]
    return {
        "processed_ids": processed,
        "skipped_ids": skipped,
    }
