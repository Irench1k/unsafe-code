"""Restaurant Validators - JSON-only input validation and response serialization.

All /restaurants endpoints require JSON bodies. No form data or query params for mutations.
"""

from decimal import Decimal
from typing import Any

from flask import request

from ..database.models import Coupon, MenuItem, Order, Refund, Restaurant, User
from ..database.repository import find_restaurant_by_id
from ..errors import CheekyApiError


# ============================================================
# JSON INPUT HELPERS
# ============================================================
def require_json_body() -> dict:
    """Require a JSON body in the request. Raises if not JSON or not a dict."""
    if not request.is_json:
        raise CheekyApiError("Content-Type must be application/json")
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise CheekyApiError("Request body must be a JSON object")
    return data


def require_condition(condition: Any, message: str) -> None:
    """Raise CheekyApiError if condition is falsy."""
    if not condition:
        raise CheekyApiError(message)


# ============================================================
# RESTAURANT RESOLUTION
# ============================================================
def get_trusted_restaurant(restaurant_id: int) -> Restaurant:
    """Resolve and validate restaurant exists."""
    restaurant = find_restaurant_by_id(restaurant_id)
    require_condition(restaurant, f"Restaurant {restaurant_id} not found")
    return restaurant


# ============================================================
# INPUT VALIDATION - MENU ITEMS
# ============================================================
def validate_menu_item_fields(
    *,
    require_name: bool = False,
    require_price: bool = False,
    require_any: bool = False,
) -> dict:
    """Validate menu item fields from JSON body."""
    data = require_json_body()
    fields: dict = {}

    name = data.get("name")
    if name is not None:
        require_condition(isinstance(name, str) and name.strip(), "name must be a non-empty string")
        fields["name"] = name.strip()
    elif require_name:
        raise CheekyApiError("name is required")

    price = data.get("price")
    if price is not None:
        require_condition(
            isinstance(price, (int, float, str, Decimal)),
            "price must be a number"
        )
        try:
            price_decimal = Decimal(str(price))
        except Exception:
            raise CheekyApiError("price must be a valid decimal") from None
        require_condition(price_decimal > 0, "price must be positive")
        fields["price"] = price_decimal
    elif require_price:
        raise CheekyApiError("price is required")

    available = data.get("available")
    if available is not None:
        require_condition(isinstance(available, bool), "available must be a boolean")
        fields["available"] = available

    if require_any:
        require_condition(bool(fields), "No fields provided")

    return fields


# ============================================================
# INPUT VALIDATION - RESTAURANT REGISTRATION/UPDATE
# ============================================================
def validate_restaurant_registration(verified_token: dict[str, Any] | None) -> dict:
    """Parse and validate restaurant registration from verified token."""
    require_condition(verified_token, "Verified token is required")

    name = verified_token["name"]
    description = verified_token["description"]
    domain = verified_token["domain"]
    owner = verified_token["owner"]

    require_condition(name and description, "name and description are required")

    return {
        "name": name,
        "description": description,
        "domain": domain,
        "owner": owner,
    }


def validate_restaurant_update(verified_token: dict[str, Any] | None) -> dict:
    """Parse and validate restaurant update from JSON body or verified token."""
    if verified_token:
        return {
            "name": verified_token["name"],
            "description": verified_token["description"],
            "domain": verified_token["domain"],
        }
    else:
        # No token -> update restaurant with insecure data; DO NOT UPDATE DOMAIN THIS WAY!
        data = require_json_body()
        return {
            "name": data.get("name"),
            "description": data.get("description"),
            "domain": None,  # Domain requires verified token
        }


# ============================================================
# INPUT VALIDATION - BATCH REFUND
# ============================================================
def validate_batch_refund_request() -> tuple[list[int], str]:
    """Validate batch refund request. Returns (order_ids, reason).

    Expects JSON: { "order_ids": [1, 2, 3], "reason": "Quality issue" }
    """
    data = require_json_body()

    order_ids = data.get("order_ids")
    require_condition(order_ids is not None, "order_ids is required")
    require_condition(isinstance(order_ids, list), "order_ids must be a list")
    require_condition(len(order_ids) > 0, "order_ids cannot be empty")
    require_condition(
        all(isinstance(oid, int) for oid in order_ids),
        "order_ids must be a list of integers"
    )

    reason = data.get("reason", "Batch refund initiated by restaurant")
    require_condition(isinstance(reason, str), "reason must be a string")

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
    skipped = [{"order_id": r["order_id"], "reason": r["reason"]} for r in results if r["status"] == "skipped"]
    return {
        "processed_ids": processed,
        "skipped_ids": skipped,
    }
