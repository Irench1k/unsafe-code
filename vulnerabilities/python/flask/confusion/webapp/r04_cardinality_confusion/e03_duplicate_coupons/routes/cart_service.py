"""
Cart Service - Business Logic Layer

This module handles all cart business operations:
- Adding items to cart
- Processing shareable coupons
- Checkout workflow (coupon application, price calculation, order creation)

NO Flask imports here - all Flask context accessed via parameters.
"""

import logging
from decimal import Decimal

from flask import session

from ..auth.authenticators import CustomerAuthenticator
from ..config import OrderConfig
from ..database.models import Cart, CartItem, Coupon, CouponType, Order, OrderItem
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
from ..database.services import add_item_to_cart as repo_add_item
from ..errors import CheekyApiError

logger = logging.getLogger(__name__)


# ============================================================
# CART ITEM MANAGEMENT
# ============================================================
def add_item_to_cart(
    cart: Cart,
    item_id: int | None,
    quantity: int,
    coupon_code: str | None,
) -> None:
    """
    Add an item to cart with optional coupon.

    Args:
        cart: The cart to add item to
        item_id: Menu item ID (optional - can add just coupon)
        quantity: Number of items to add
        coupon_code: Optional coupon code to apply

    Raises:
        CheekyApiError: If item not found, unavailable, or coupon invalid
    """
    if item_id:
        menu_item = find_menu_item_by_id(item_id)
        if not menu_item:
            raise CheekyApiError(f"Menu item {item_id} not found")
        if not menu_item.available:
            raise CheekyApiError(f"Menu item {item_id} is not available")
        if menu_item.restaurant_id != cart.restaurant_id:
            raise CheekyApiError(
                f"Menu item {item_id} does not belong to restaurant {cart.restaurant_id}"
            )
        if quantity <= 0:
            raise CheekyApiError("Quantity must be positive")

        repo_add_item(cart.id, menu_item.id, menu_item.name, menu_item.price, quantity)

    if coupon_code:
        coupon = find_coupon_by_code(coupon_code)
        if not coupon:
            raise CheekyApiError(f"Coupon {coupon_code} not found")
        if coupon.restaurant_id != cart.restaurant_id:
            raise CheekyApiError(
                f"Coupon {coupon_code} does not belong to restaurant {cart.restaurant_id}"
            )
        # Single-use coupons must be applied at checkout
        if coupon.single_use:
            raise CheekyApiError("Single-use coupons must be applied at checkout")

        # Only one coupon per cart
        cart_items = get_cart_items(cart.id)
        if all(item.coupon_id is None for item in cart_items):
            add_coupon_to_cart(cart, coupon)
        else:
            logger.warning(f"Coupon {coupon_code} not applied - cart already has coupon")


# ============================================================
# SHAREABLE COUPON HANDLING
# ============================================================
def process_shareable_coupon(coupon_code: str) -> str:
    """
    Process a shareable coupon link and return redirect URL.

    Handles different scenarios:
    - New customers: Store coupon, redirect to registration
    - Logged in with cart: Apply coupon, redirect to checkout
    - Logged in without cart: Store coupon, redirect to menu
    - Mobile app: Return app deep link

    Args:
        coupon_code: The coupon code from the link

    Returns:
        URL to redirect the user to

    Raises:
        CheekyApiError: If coupon is invalid or single-use
    """
    coupon = find_coupon_by_code(coupon_code)
    if not coupon:
        raise CheekyApiError(f"Coupon {coupon_code} not found")
    if coupon.single_use:
        raise CheekyApiError("Coupon invalid")

    # Check if user is logged in
    authenticator = CustomerAuthenticator()
    if not authenticator.authenticate():
        session["coupon_code"] = coupon_code
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
        session["coupon_code"] = coupon_code
        return "https://app.cheeky.sea/menu"

    # Mobile app users
    return f"cheekysea://cart/apply-coupons?code={coupon_code}"


# ============================================================
# CHECKOUT ORCHESTRATION
# ============================================================
def process_checkout(
    cart: Cart,
    user_id: int,
    balance: Decimal,
    tip: Decimal,
    delivery_address: str,
    coupon_codes: list[str],
    valid_single_use_coupons: set[str],
) -> Order:
    """
    Process a complete checkout transaction.

    This orchestrates the full checkout flow:
    1. Validate cart has items
    2. Calculate prices with coupon discounts
    3. Verify sufficient balance
    4. Charge the customer
    5. Create and save the order
    6. Mark single-use coupons as used

    Args:
        cart: The cart being checked out
        user_id: ID of the customer
        balance: Customer's current balance
        tip: Tip amount
        delivery_address: Delivery address string
        coupon_codes: Original list of coupon codes from request (may have duplicates)
        valid_single_use_coupons: Deduplicated set of validated coupon codes

    Returns:
        The created Order object

    Raises:
        CheekyApiError: If validation fails or insufficient funds
    """
    # Get cart items
    cart_items = get_cart_items(cart.id)
    if not cart_items:
        raise CheekyApiError(f"Cart {cart.id} is empty")

    # Calculate prices (this is where the vulnerability lives!)
    subtotal, delivery_fee, discount = calculate_order_total(
        cart_items, coupon_codes, valid_single_use_coupons
    )
    if subtotal is None:
        raise CheekyApiError("Some items in cart are no longer available")

    if subtotal < 0:
        raise CheekyApiError("Subtotal is negative")

    # Calculate total and verify funds
    total_amount = subtotal + delivery_fee + tip
    if total_amount < 0:
        raise CheekyApiError("Total amount is negative")
    if balance < total_amount:
        raise CheekyApiError("Insufficient balance")

    # Charge customer
    charge_user(user_id, total_amount)

    # Create order and items
    order, order_items = create_order_from_cart(
        user_id=user_id,
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

    logger.info(f"Order {order.id} created for user {user_id}, total: ${total_amount}")
    return order


# ============================================================
# PRICE CALCULATION
# ============================================================
def calculate_order_total(
    cart_items: list[CartItem],
    coupon_codes: list[str],
    valid_single_use_coupons: set[str],
) -> tuple[Decimal, Decimal, Decimal] | tuple[None, None, None]:
    """
    Calculate order totals including coupon discounts.

    Args:
        cart_items: Items in the cart
        coupon_codes: Original coupon codes from request (may contain duplicates)
        valid_single_use_coupons: Deduplicated set of validated coupon codes

    Returns:
        (subtotal, delivery_fee, discount) on success, (None, None, None) if items unavailable
    """
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
    """
    Apply single-use coupons to cart items and return total discount.

    This applies coupons from the checkout request to eligible cart items.
    Each coupon can only be applied to one item (matching item_id), and each
    item can only have one coupon applied.

    Args:
        cart_items: Items in the cart
        coupon_codes: Original list of coupon codes from request (may have duplicates)
        valid_single_use_coupons: Deduplicated set of validated coupon codes

    Returns:
        Total discount amount applied
    """
    total_discount = Decimal("0.00")
    items_with_coupon_applied: set[int] = set()

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

        # Only process if this is a validated single-use coupon
        # NOTE: We check against the deduplicated set, but iterate the original list
        if coupon.code not in valid_single_use_coupons:
            continue

        # Find a matching cart item that hasn't had a coupon applied yet
        for item in cart_items:
            if item.item_id == coupon.item_id and item.id not in items_with_coupon_applied:
                # Apply the discount
                discount = _calculate_coupon_discount(coupon, item.price)
                total_discount += discount
                items_with_coupon_applied.add(item.id)
                logger.info(
                    f"Applied single-use coupon {coupon.code} to item {item.item_id}, "
                    f"discount: ${discount}"
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
        raise CheekyApiError(f"Invalid coupon type: {coupon.type.value}")


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
    """
    Create an order and order items from cart contents.

    Creates order item snapshots with reservation checking.
    """
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
    """
    Mark single-use coupons as used after successful checkout.

    Args:
        valid_single_use_coupons: Set of validated coupon codes (DB format with CODE- prefix)
    """
    for coupon_code in valid_single_use_coupons:
        # The set contains DB-format codes (e.g., "CODE-KRABBY90-PROMO1")
        # We need to strip the CODE- prefix for find_coupon_by_code
        user_code = coupon_code.replace("CODE-", "", 1)
        coupon = find_coupon_by_code(user_code)
        if coupon and coupon.single_use:
            coupon.used = True
            save_coupon(coupon)
            logger.info(f"Marked coupon {coupon.code} as used")
