"""
Cart Validators - Input Validation, Authorization, and Response Serialization

This module handles:
- Cart resolution and authorization
- Input validation for cart operations
- Response serialization for cart and order responses
"""

import logging
from decimal import Decimal, InvalidOperation

from flask import g, request, session

from ..database.models import Cart, Order
from ..database.repository import (
    find_cart_by_id,
    find_coupon_by_code,
    find_order_items,
    get_cart_items,
)
from ..errors import CheekyApiError

logger = logging.getLogger(__name__)


# ============================================================
# CART RESOLUTION & AUTHORIZATION
# ============================================================
def get_trusted_cart() -> Cart:
    """
    Resolve and authorize the cart for the current request.

    Prefers the signed cart ID from session, falls back to path for legacy mobile.
    Validates ownership and that cart is active.

    Returns:
        The authorized Cart object

    Raises:
        CheekyApiError: If cart not found, not owned, or not active
    """
    cart_id = session.get("cart_id") or g.get("cart_id")
    if not cart_id:
        raise CheekyApiError("Cart ID is required")

    cart = find_cart_by_id(cart_id)
    if not cart:
        raise CheekyApiError(f"Cart {cart_id} not found")

    if cart.user_id != g.get("user_id"):
        raise CheekyApiError("Cart does not belong to user")

    if not cart.active:
        raise CheekyApiError(f"Cart {cart_id} is not active")

    return cart


# ============================================================
# INPUT VALIDATION
# ============================================================
def extract_single_use_coupons(coupon_codes: list[str]) -> set[str]:
    """
    Validate and deduplicate single-use coupon codes.

    Returns only valid single-use coupons that haven't been used yet.
    The returned set is deduplicated, preventing duplicate application
    at the validation layer.

    Args:
        coupon_codes: Raw list of coupon codes from request (may have duplicates)

    Returns:
        Set of valid, unused, single-use coupon codes (deduplicated)
    """
    single_use_coupons = set()
    for coupon_code in coupon_codes:
        coupon = find_coupon_by_code(coupon_code)
        if coupon and coupon.single_use and not coupon.used:
            single_use_coupons.add(coupon.code)
    return single_use_coupons


def validate_checkout_request() -> dict:
    """
    Parse and validate checkout request body.

    Expects JSON with:
    - tip: Optional decimal amount
    - delivery_address: String address
    - coupon_codes: Optional list of coupon codes

    Returns:
        Dictionary with validated checkout parameters

    Raises:
        CheekyApiError: If request body is invalid
    """
    if not request.is_json:
        raise CheekyApiError("Request body must be JSON")

    body = request.json or {}

    # Parse tip amount
    tip = Decimal("0.00")
    if "tip" in body:
        try:
            tip = abs(Decimal(str(body["tip"])).quantize(Decimal("0.01")))
        except (InvalidOperation, TypeError):
            raise CheekyApiError("Invalid tip amount") from None

    # Parse delivery address
    delivery_address = str(body.get("delivery_address", ""))

    # Parse coupon codes
    coupon_codes = []
    if "coupon_codes" in body:
        raw_codes = body["coupon_codes"]
        if isinstance(raw_codes, list) and all(isinstance(c, str) for c in raw_codes):
            coupon_codes = raw_codes
        else:
            raise CheekyApiError("coupon_codes must be an array of strings")

    return {
        "tip": tip,
        "delivery_address": delivery_address,
        "coupon_codes": coupon_codes,
    }


# ============================================================
# RESPONSE SERIALIZATION
# ============================================================
def serialize_cart(cart: Cart) -> dict:
    """Serialize cart to JSON-compatible dict with items."""
    cart_items = get_cart_items(cart.id)
    return {
        "cart_id": cart.id,
        "restaurant_id": cart.restaurant_id,
        "items": [
            {
                "item_id": item.item_id,
                "name": item.name,
                "price": str(item.price),
                "coupon_id": item.coupon_id,
                "quantity": item.quantity,
            }
            for item in cart_items
        ],
    }


def serialize_order(order: Order) -> dict:
    """Serialize order to JSON-compatible dict with items."""
    order_items = find_order_items(order.id)
    return {
        "order_id": order.id,
        "restaurant_id": order.restaurant_id,
        "user_id": order.user_id,
        "total": str(order.total),
        "delivery_fee": str(order.delivery_fee),
        "delivery_address": order.delivery_address,
        "tip": str(order.tip),
        "discount": str(order.discount),
        "created_at": order.created_at.isoformat(),
        "items": [
            {
                "item_id": item.item_id,
                "name": item.name,
                "price": str(item.price),
            }
            for item in order_items
        ],
        "status": order.status.value,
    }
