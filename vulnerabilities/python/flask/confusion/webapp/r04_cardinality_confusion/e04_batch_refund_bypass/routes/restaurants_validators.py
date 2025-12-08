"""Restaurant Validators - input validation, authorization, and response serialization."""

import logging
from typing import Any

from flask import request

from ..database.models import Coupon, MenuItem, Restaurant, User
from ..database.repository import find_menu_item_by_id, find_restaurant_by_id
from ..errors import CheekyApiError
from ..utils import get_boolean_param, get_decimal_param, get_param, require_condition

logger = logging.getLogger(__name__)


# ============================================================
# RESTAURANT RESOLUTION & AUTHORIZATION
# ============================================================
def get_trusted_restaurant(restaurant_id: int) -> Restaurant:
    """Resolve and validate restaurant exists."""
    restaurant = find_restaurant_by_id(restaurant_id)
    require_condition(restaurant, f"Restaurant {restaurant_id} not found")
    return restaurant


# ============================================================
# INPUT VALIDATION
# ============================================================
def validate_menu_item_fields(
    *,
    require_name: bool = False,
    require_price: bool = False,
    require_any: bool = False,
) -> dict:
    """Normalize menu item payload and enforce requirements."""
    fields: dict = {}

    name = get_param("name")
    if name is not None:
        require_condition(name.strip(), "name cannot be empty")
        fields["name"] = name
    elif require_name:
        raise CheekyApiError("name is required")

    price_raw = get_param("price")
    if price_raw is not None:
        price = get_decimal_param("price")
        require_condition(price is not None, "price must be a decimal value")
        require_condition(price > 0, "price must be positive")
        fields["price"] = price
    elif require_price:
        raise CheekyApiError("price is required")

    available_raw = get_param("available")
    if available_raw is not None:
        available = get_boolean_param("available")
        require_condition(available is not None, "available must be a boolean value")
        fields["available"] = available

    if require_any:
        require_condition(bool(fields), "No fields provided")

    return fields


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
    """Parse and validate restaurant update from token or request params."""
    if verified_token:
        # Extract the claims from the secure token
        return {
            "name": verified_token["name"],
            "description": verified_token["description"],
            "domain": verified_token["domain"],
        }
    else:
        # No token -> update restaurant with insecure data; DO NOT UPDATE DOMAIN THIS WAY!
        return {
            "name": get_param("name"),
            "description": get_param("description"),
            # A domain with no token should be rejected by @domain_verification_required
            "domain": None,
        }


def validate_menu_item_exists(item_id: int) -> MenuItem:
    """Validate menu item exists and return it."""
    menu_item = find_menu_item_by_id(item_id)
    require_condition(menu_item, f"Menu item {item_id} not found")
    return menu_item


# ============================================================
# RESPONSE SERIALIZATION
# ============================================================
def serialize_restaurant(restaurant: Restaurant) -> dict:
    """Serializes a restaurant to a JSON-compatible dict."""
    return {
        "id": restaurant.id,
        "name": restaurant.name,
        "description": restaurant.description,
        "domain": restaurant.domain,
    }


def serialize_restaurants(restaurants: list[Restaurant]) -> list[dict]:
    """Serializes a list of restaurants."""
    return [serialize_restaurant(restaurant) for restaurant in restaurants]


def serialize_restaurant_creation(restaurant: Restaurant) -> dict:
    """Serializes a restaurant creation to a JSON-compatible dict."""
    return {
        "id": restaurant.id,
        "name": restaurant.name,
        "description": restaurant.description,
        "owner": restaurant.owner,
        "api_key": restaurant.api_key,
        "domain": restaurant.domain,
        "status": "created",
    }


def serialize_restaurant_users(users: list[User]) -> list[dict]:
    """Serializes a list of restaurant users to JSON-compatible dicts."""
    return [{"email": user.email, "name": user.name} for user in users]


def serialize_menu_item(menu_item: MenuItem) -> dict:
    """Serializes a single menu item."""
    return {
        "id": menu_item.id,
        "restaurant_id": menu_item.restaurant_id,
        "name": menu_item.name,
        "price": str(menu_item.price),
        "available": menu_item.available,
    }


def serialize_menu_items(menu_items: list) -> list[dict]:
    """Serializes a list of menu items to JSON-compatible dicts."""
    return [serialize_menu_item(item) for item in menu_items]


def serialize_coupon(coupon: Coupon) -> dict:
    """Serializes a coupon to a JSON-compatible dict."""
    return {
        "id": coupon.id,
        "restaurant_id": coupon.restaurant_id,
        "code": coupon.code,
        "value": str(coupon.value),
    }


def serialize_coupons(coupons: list[Coupon]) -> list[dict]:
    """Serializes a list of coupons to JSON-compatible dicts."""
    return [serialize_coupon(coupon) for coupon in coupons]


# ============================================================
# BATCH REFUND VALIDATION & SERIALIZATION
# ============================================================
def validate_batch_refund_request() -> dict:
    """Parse and validate batch refund request body.

    Expects JSON: { "order_ids": [1, 2, 3], "reason": "Quality issue" }
    """
    data = request.get_json(silent=True) or {}

    order_ids_raw = data.get("order_ids")
    require_condition(order_ids_raw, "order_ids is required")
    require_condition(isinstance(order_ids_raw, list), "order_ids must be a list")
    require_condition(len(order_ids_raw) > 0, "order_ids cannot be empty")

    # Coerce each order_id to int
    order_ids: list[int] = []
    for idx, oid in enumerate(order_ids_raw):
        if isinstance(oid, int):
            order_ids.append(oid)
        elif isinstance(oid, str):
            try:
                order_ids.append(int(oid))
            except ValueError:
                raise CheekyApiError(f"order_ids[{idx}] is not a valid integer") from None
        else:
            raise CheekyApiError(f"order_ids[{idx}] must be an integer or string")

    reason = data.get("reason", "Batch refund initiated by restaurant")
    if not isinstance(reason, str):
        reason = str(reason)

    return {
        "order_ids": order_ids,
        "reason": reason,
    }


def serialize_batch_refund_result(processed_ids: list[int], skipped_ids: list[dict]) -> dict:
    """Serialize batch refund result."""
    return {
        "processed_ids": processed_ids,
        "skipped_ids": skipped_ids,
    }
