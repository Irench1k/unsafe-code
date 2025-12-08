"""Cart Validators - input validation, authorization, and response serialization."""

import logging
from decimal import Decimal, InvalidOperation

from flask import g, request, session

from ..database.models import Cart, CartItem, Coupon, MenuItem
from ..database.repository import (
    find_cart_by_id,
    find_coupon_by_code,
    find_menu_item_by_id,
    get_cart_items,
)
from ..errors import CheekyApiError
from ..utils import require_condition, require_ownership

logger = logging.getLogger(__name__)


# ============================================================
# CART RESOLUTION & AUTHORIZATION
# ============================================================
def get_trusted_cart() -> Cart:
    """Resolve and authorize cart from session or path, validating ownership."""
    cart_id = session.get("cart_id") or g.get("cart_id")
    require_condition(cart_id, "Cart ID is required")

    cart = find_cart_by_id(cart_id)
    require_condition(cart, f"Cart {cart_id} not found")
    require_ownership(cart.user_id, g.get("user_id"), "cart")
    require_condition(cart.active, f"Cart {cart_id} is not active")

    return cart


# ============================================================
# INPUT VALIDATION
# ============================================================
def extract_single_use_coupons(coupon_codes: list[str]) -> set[str]:
    """Return deduplicated set of valid, unused single-use coupon codes."""
    single_use_coupons = set()
    for coupon_code in coupon_codes:
        coupon = find_coupon_by_code(coupon_code)
        if coupon and coupon.single_use and not coupon.used:
            single_use_coupons.add(coupon.code)
    return single_use_coupons


def validate_checkout_request() -> dict:
    """Parse and validate checkout JSON body (tip, delivery_address, coupon_codes)."""
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


# ============================================================
# ITEM AND COUPON VALIDATION
# ============================================================
def validate_menu_item_for_cart(cart: Cart, item_id: int, quantity: int) -> MenuItem:
    """Validate item exists, is available, belongs to cart's restaurant, and quantity > 0."""
    menu_item = find_menu_item_by_id(item_id)
    require_condition(menu_item, f"Menu item {item_id} not found")
    require_condition(menu_item.available, f"Menu item {item_id} is not available")
    require_condition(
        menu_item.restaurant_id == cart.restaurant_id,
        f"Menu item {item_id} does not belong to restaurant {cart.restaurant_id}",
    )
    require_condition(quantity > 0, "Quantity must be positive")
    return menu_item


def validate_coupon_for_cart(cart: Cart, coupon_code: str) -> Coupon:
    """Validate coupon for add-item flow. Single-use coupons rejected (checkout only)."""
    coupon = find_coupon_by_code(coupon_code)
    require_condition(coupon, f"Coupon {coupon_code} not found")
    require_condition(
        coupon.restaurant_id == cart.restaurant_id,
        f"Coupon {coupon_code} does not belong to restaurant {cart.restaurant_id}",
    )
    require_condition(not coupon.single_use, "Single-use coupons must be applied at checkout")
    return coupon


def validate_shareable_coupon(coupon_code: str) -> Coupon:
    """Validate coupon for shareable links. Single-use coupons rejected."""
    coupon = find_coupon_by_code(coupon_code)
    require_condition(coupon, f"Coupon {coupon_code} not found")
    require_condition(not coupon.single_use, "Coupon invalid")
    return coupon


def validate_cart_for_checkout(cart: Cart) -> list[CartItem]:
    """Validate cart has items and return them."""
    cart_items = get_cart_items(cart.id)
    require_condition(cart_items, f"Cart {cart.id} is empty")
    return cart_items


