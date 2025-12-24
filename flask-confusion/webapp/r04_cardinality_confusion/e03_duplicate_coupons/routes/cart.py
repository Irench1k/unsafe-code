"""Cart Controller - delegates to cart_validators.py and cart_service.py."""

import logging

from flask import Blueprint, g, redirect, session

from ..auth.decorators import require_auth
from ..database.repository import find_cart_by_id, find_restaurant_by_id
from ..database.services import add_item_to_cart, create_cart, serialize_order
from ..utils import (
    created_response,
    get_int_param,
    get_param,
    get_restaurant_id,
    require_condition,
    success_response,
)
from . import cart_service
from .cart_validators import (
    extract_single_use_coupons,
    get_trusted_cart,
    serialize_cart,
    validate_cart_for_checkout,
    validate_checkout_request,
    validate_coupon_for_cart,
    validate_menu_item_for_cart,
    validate_shareable_coupon,
)

bp = Blueprint("cart", __name__, url_prefix="/cart")
logger = logging.getLogger(__name__)


@bp.url_value_preprocessor
def preprocess_cart_id(endpoint, values):
    """Store cart_id from path for later resolution."""
    if "cart_id" in values:
        g.cart_id = values.pop("cart_id")


# ============================================================
# CART ENDPOINTS
# ============================================================
@bp.post("")
@require_auth(["customer"])
def create_new_cart():
    """Create a new empty cart or return existing one."""
    # Return existing cart if active
    if "cart_id" in session:
        existing_cart = find_cart_by_id(session["cart_id"])
        if existing_cart and existing_cart.user_id == g.user_id:
            return success_response(serialize_cart(existing_cart))

    # Create new cart
    restaurant_id = get_restaurant_id()
    restaurant = find_restaurant_by_id(restaurant_id)
    require_condition(restaurant, f"Restaurant {restaurant_id} not found")

    new_cart = create_cart(restaurant_id, g.user_id)
    session["cart_id"] = new_cart.id
    return created_response(serialize_cart(new_cart))


@bp.post("/<int:cart_id>/items")
@require_auth(["customer"])
def add_item_to_cart_endpoint():
    """Add item to cart."""
    cart = get_trusted_cart()
    item_id = get_int_param("item_id")
    quantity = get_int_param("quantity", 1)
    coupon_code = get_param("coupon_code")

    if item_id:
        menu_item = validate_menu_item_for_cart(cart, item_id, quantity)
        add_item_to_cart(cart.id, menu_item.id, menu_item.name, menu_item.price, quantity)

    if coupon_code:
        coupon = validate_coupon_for_cart(cart, coupon_code)
        cart_service.apply_coupon_to_cart_if_allowed(cart, coupon)

    return success_response(serialize_cart(cart))


@bp.get("/apply-coupons")
def add_coupons_to_cart_endpoint():
    """Apply coupons via shareable links."""
    coupon_code = get_param("code")
    require_condition(coupon_code, "Coupon code is required")

    coupon = validate_shareable_coupon(coupon_code)
    redirect_url = cart_service.process_shareable_coupon(coupon, coupon_code)
    return redirect(redirect_url)


@bp.post("/<int:cart_id>/checkout")
@require_auth(["customer"])
def checkout_cart():
    """Checkout cart and create order."""
    cart = get_trusted_cart()
    checkout_data = validate_checkout_request()
    cart_items = validate_cart_for_checkout(cart)

    # Merge session coupon (from shareable link) with body coupon_codes
    coupon_codes = list(checkout_data.get("coupon_codes", []))
    session_coupon = session.pop("coupon_code", None)
    if session_coupon:
        coupon_codes.append(session_coupon)

    # Extract validated single-use coupons (deduplicated)
    valid_single_use_coupons = extract_single_use_coupons(coupon_codes)

    # Clear cart from session before checkout
    session.pop("cart_id", None)

    # Process checkout (service handles balance check after calculating real total)
    order = cart_service.process_checkout(
        cart=cart,
        user=g.user,
        cart_items=cart_items,
        tip=checkout_data["tip"],
        delivery_address=checkout_data["delivery_address"],
        coupon_codes=coupon_codes,
        valid_single_use_coupons=valid_single_use_coupons,
    )

    return created_response(serialize_order(order))
