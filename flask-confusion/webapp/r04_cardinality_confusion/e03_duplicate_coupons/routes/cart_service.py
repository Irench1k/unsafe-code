"""Cart Service - business logic for cart operations and checkout."""

import logging
from decimal import Decimal

from flask import session

from ..auth.authenticators import CustomerAuthenticator
from ..config import OrderConfig
from ..database.models import Cart, CartItem, Coupon, CouponType, Order, OrderItem, User
from ..database.repository import (
    find_coupon_by_code,
    find_menu_item_by_id,
    get_cart_items,
    reserve_if_available,
    save_coupon,
    save_order,
    save_order_items,
)
from ..database.services import add_coupon_to_cart, charge_user
from ..errors import CheekyApiError
from ..utils import require_condition

logger = logging.getLogger(__name__)


# ============================================================
# CART ITEM MANAGEMENT
# ============================================================
def apply_coupon_to_cart_if_allowed(cart: Cart, coupon: Coupon) -> bool:
    """Apply coupon to cart if no coupon already applied. Returns success."""
    cart_items = get_cart_items(cart.id)
    if all(item.coupon_id is None for item in cart_items):
        add_coupon_to_cart(cart, coupon)
        return True
    logger.warning(f"Coupon {coupon.code} not applied - cart already has coupon")
    return False


# ============================================================
# SHAREABLE COUPON HANDLING
# ============================================================
def process_shareable_coupon(coupon: Coupon, user_code: str) -> str:
    """Process shareable coupon link and return appropriate redirect URL.

    Args:
        coupon: The validated coupon object
        user_code: The original user-provided code (without CODE- prefix)
    """
    # Check if user is logged in
    authenticator = CustomerAuthenticator()
    if not authenticator.authenticate():
        session["coupon_code"] = user_code  # Store user format for find_coupon_by_code
        return "https://app.cheeky.sea/register"

    # Try to apply to existing cart
    try:
        from .cart_validators import get_trusted_cart

        cart = get_trusted_cart()
        cart_items = get_cart_items(cart.id)
        if all(item.coupon_id is None for item in cart_items):
            add_coupon_to_cart(cart, coupon)
            return f"https://app.cheeky.sea/cart/{cart.id}/checkout"
    except CheekyApiError:
        pass

    # Cookie-based session but no cart
    if session.get("email"):
        session["coupon_code"] = user_code  # Store user format for find_coupon_by_code
        return "https://app.cheeky.sea/menu"

    # Mobile app users
    return f"cheekysea://cart/apply-coupons?code={user_code}"


# ============================================================
# CHECKOUT ORCHESTRATION
# ============================================================
def process_checkout(
    cart: Cart,
    user: User,
    cart_items: list[CartItem],
    tip: Decimal,
    delivery_address: str,
    coupon_codes: list[str],
    valid_single_use_coupons: set[str],
) -> Order:
    """Process complete checkout: calculate totals, charge user, create order."""
    # Calculate prices (this is where the vulnerability lives!)
    subtotal, delivery_fee, discount = calculate_order_total(
        cart_items, coupon_codes, valid_single_use_coupons
    )
    require_condition(subtotal is not None, "Some items in cart are no longer available")
    require_condition(subtotal >= 0, "Subtotal is negative")

    # Calculate total and verify balance
    total_amount = subtotal + delivery_fee + tip
    require_condition(total_amount >= 0, "Total amount is negative")
    require_condition(user.balance >= total_amount, "Insufficient balance")

    # Charge customer
    charge_user(user.id, total_amount)

    # Create order and items
    order, order_items = create_order_from_cart(
        user_id=user.id,
        restaurant_id=cart.restaurant_id,
        total=total_amount,
        cart_items=cart_items,
        delivery_fee=delivery_fee,
        delivery_address=delivery_address,
        tip=tip,
        discount=discount,
    )

    # Persist order
    save_order(order)
    for item in order_items:
        item.order_id = order.id
    save_order_items(order_items)

    # Mark coupons as used AFTER successful checkout
    mark_coupons_used(valid_single_use_coupons)

    logger.info(f"Order {order.id} created for user {user.id}, total: ${total_amount}")
    return order


# ============================================================
# PRICE CALCULATION
# ============================================================
def calculate_order_total(
    cart_items: list[CartItem],
    coupon_codes: list[str],
    valid_single_use_coupons: set[str],
) -> tuple[Decimal, Decimal, Decimal] | tuple[None, None, None]:
    """Calculate (subtotal, delivery_fee, discount) or (None, None, None) if items unavailable."""
    # Check all items still available
    for item in cart_items:
        menu_item = find_menu_item_by_id(item.item_id)
        if not menu_item or not menu_item.available:
            return None, None, None

    # Calculate base subtotal
    subtotal = sum(item.price * item.quantity for item in cart_items)

    # Apply buy-x-get-y coupons attached to cart items
    for item in cart_items:
        if item.coupon_id:
            from ..database.repository import find_coupon_by_id

            coupon = find_coupon_by_id(item.coupon_id)
            if not coupon or coupon.type != CouponType.buy_x_get_y_free:
                continue

            if item.quantity >= coupon.value:
                logger.info(f"Buy-X-Get-Y coupon {coupon.code} applied to item {item.item_id}")
                subtotal -= item.price

    # Apply single-use checkout coupons
    discount = apply_coupons_to_order_items(cart_items, coupon_codes, valid_single_use_coupons)
    subtotal -= discount

    # Calculate delivery fee
    delivery_fee = (
        Decimal("0.00") if subtotal > OrderConfig.FREE_DELIVERY_ABOVE else OrderConfig.DELIVERY_FEE
    )

    return subtotal, delivery_fee, discount


def apply_coupons_to_order_items(
    cart_items: list[CartItem],
    coupon_codes: list[str],
    valid_single_use_coupons: set[str],
) -> Decimal:
    """Apply checkout coupons (single-use and non-single-use) to eligible cart items."""
    total_discount = Decimal("0.00")

    # @unsafe {
    #     "vuln_id": "v403",
    #     "severity": "medium",
    #     "category": "cardinality-confusion",
    #     "description": "Iterates original coupon_codes list while checking against deduplicated set, allowing duplicates to apply discount multiple times",
    #     "cwe": "CWE-345"
    # }
    # Process coupons in the order they appear in the request
    for coupon_code in coupon_codes:
        # Look up the coupon by the user-provided code
        coupon = find_coupon_by_code(coupon_code)
        if not coupon:
            continue

        # For single-use coupons: check against deduplicated set (vuln: iterate original list)
        # For non-single-use coupons: apply once per coupon code
        if coupon.single_use and coupon.code not in valid_single_use_coupons:
            # Only process if this is a validated single-use coupon
            continue

        # Find a matching cart item that hasn't had a coupon applied yet
        for item in cart_items:
            if item.item_id == coupon.item_id and not item.coupon_id:
                # Apply the discount
                discount = _calculate_coupon_discount(coupon, item.price)
                total_discount += discount
                item.coupon_id = coupon.id
                logger.info(
                    f"Applied {'single-use' if coupon.single_use else 'reusable'} coupon "
                    f"{coupon.code} to item {item.item_id}, discount: ${discount}"
                )
                break

    return total_discount


def _calculate_coupon_discount(coupon: Coupon, price: Decimal) -> Decimal:
    """Calculate the discount amount for a coupon applied to an item."""
    if coupon.type == CouponType.fixed_amount:
        return min(coupon.value, price)
    elif coupon.type == CouponType.discount_percent:
        return (price * coupon.value / 100).quantize(Decimal("0.01"))
    elif coupon.type == CouponType.free_item_sku:
        return price
    elif coupon.type == CouponType.buy_x_get_y_free:
        # This type is handled separately in calculate_order_total
        return Decimal("0.00")
    else:
        # This should never happen with valid data - programming error
        raise ValueError(f"Invalid coupon type: {coupon.type.value}")


# ============================================================
# ORDER CREATION
# ============================================================
def create_order_from_cart(
    user_id: int,
    restaurant_id: int,
    total: Decimal,
    cart_items: list[CartItem],
    delivery_fee: Decimal,
    delivery_address: str,
    tip: Decimal = Decimal("0.00"),
    discount: Decimal = Decimal("0.00"),
) -> tuple[Order, list[OrderItem]]:
    """Create Order and OrderItems from cart, with reservation checking."""
    order = Order(
        restaurant_id=restaurant_id,
        user_id=user_id,
        total=total,
        delivery_fee=delivery_fee,
        delivery_address=delivery_address,
        tip=tip,
        discount=discount,
    )

    # Create order items with availability checking
    order_items = []
    for item in cart_items:
        quantity_remaining = item.quantity
        while reserve_if_available(item.item_id) and quantity_remaining > 0:
            order_items.append(
                OrderItem(
                    item_id=item.item_id,
                    name=item.name,
                    price=item.price,
                    coupon_id=item.coupon_id,
                )
            )
            quantity_remaining -= 1

    return order, order_items


# ============================================================
# COUPON MANAGEMENT
# ============================================================
def mark_coupons_used(valid_single_use_coupons: set[str]) -> None:
    """Mark single-use coupons as used after successful checkout."""
    for coupon_code in valid_single_use_coupons:
        # The set contains DB-format codes (e.g., "CODE-KRABBY90-PROMO1")
        # We need to strip the CODE- prefix for find_coupon_by_code
        user_code = coupon_code.replace("CODE-", "", 1)
        coupon = find_coupon_by_code(user_code)
        if coupon and coupon.single_use:
            coupon.used = True
            save_coupon(coupon)
            logger.info(f"Marked coupon {coupon.code} as used")
