"""
Business Logic Layer

Contains high-level business operations that coordinate multiple repository calls
and enforce business rules. No direct database access - all operations go through
the repository.
"""

import logging
from decimal import Decimal
from typing import Literal

from flask import g, session

from ..errors import CheekyApiError
from .models import Cart, Order, OrderItem, Refund, RefundStatus, User
from .repository import (
    add_cart_item,
    delete_order,
    find_cart_by_id,
    find_menu_item_by_id,
    find_order_by_id,
    find_order_items,
    find_orders_by_user,
    find_user_by_email,
    find_user_by_id,
    get_cart_items,
    get_refund_by_order_id,
    get_signup_bonus_remaining,
    save_cart,
    save_order,
    save_order_items,
    save_refund,
    save_user,
    set_signup_bonus_remaining,
)

logger = logging.getLogger(__name__)


# ============================================================
# MENU SERVICES
# ============================================================
def serialize_menu_items(menu_items: list) -> list[dict]:
    """Serializes a list of menu items to JSON-compatible dicts."""
    return [
        {
            "id": item.id,
            "restaurant_id": item.restaurant_id,
            "name": item.name,
            "price": str(item.price),
            "available": item.available,
        }
        for item in menu_items
    ]


# ============================================================
# USER SERVICES
# ============================================================
def create_user(email: str, password: str, name: str) -> None:
    """Creates a new user."""
    user = User(email=email, name=name, password=password)
    save_user(user)
    logger.info(f"User created: {email}")


def apply_signup_bonus(email: str) -> None:
    """Applies a signup bonus to a newly registered user."""
    user = find_user_by_email(email)
    if not user:
        logger.warning(f"Cannot apply signup bonus - user not found: {email}")
        return

    bonus_amount = Decimal("2.00")
    remaining = get_signup_bonus_remaining()

    if remaining < bonus_amount:
        logger.warning(f"Insufficient signup bonus remaining for {email}: {remaining}")
        return

    user.balance += bonus_amount
    save_user(user)
    set_signup_bonus_remaining(remaining - bonus_amount)
    logger.info(f"Signup bonus applied to {email}: {bonus_amount}")


def increment_user_balance(email: str, amount: Decimal) -> Decimal | None:
    """Increments a user's balance and returns the new balance."""
    user = find_user_by_email(email)
    if not user:
        logger.warning(f"Cannot increment balance - user not found: {email}")
        return None

    user.balance += amount
    save_user(user)
    logger.info(f"Balance updated for {email}: +{amount} = {user.balance}")
    return user.balance


def get_current_user(email: str | None = None) -> User | None:
    """Gets the current user from the database."""

    user_email = email or getattr(g, "email", None) or session.get("email")
    if not user_email:
        logger.warning("No email provided and no user in request context")
        return None

    return find_user_by_email(user_email)


# ============================================================
# ORDER SERVICES
# ============================================================
def create_order_from_checkout(
    user_id: int,
    restaurant_id: int,
    total: Decimal,
    items: list[dict],
    delivery_fee: Decimal,
    delivery_address: str,
    tip: Decimal = Decimal("0.00"),
) -> Order:
    """Creates a new order and its order item snapshots."""
    order = Order(
        restaurant_id=restaurant_id,
        user_id=user_id,
        total=total,
        delivery_fee=delivery_fee,
        delivery_address=delivery_address,
        tip=tip,
    )

    # Create order items separately
    order_items = [
        OrderItem(
            item_id=int(item["item_id"]),
            name=item["name"],
            price=Decimal(str(item["price"])),
        )
        for item in items
    ]

    return order, order_items


def save_order_securely(order: Order, order_items: list[OrderItem]) -> None:
    """
    Charge customer and save order in DB, now with idempotency & rollback!

    This is a transactional operation that ensures data consistency:
    - Charges the user
    - Saves the order
    - Saves the order items
    - Rolls back both operations if anything fails
    """
    charged_successfully = False

    try:
        charged_successfully = charge_user(order.user_id, order.total)
        save_order(order)
        for item in order_items:
            item.order_id = order.id
        save_order_items(order_items)
        logger.info(f"Order saved: {order.id} for user {order.user_id}")
    except Exception as e:
        logger.error(f"Order save failed: {order.id} - {e}")
        # Rollback routine: refund the customer if we charged them + remove the order from the database
        if charged_successfully:
            refund_user(order.user_id, order.total)

        # Remove the order from the database
        if order.id:
            delete_order(order.id)
        raise


def get_user_orders(user_id: int) -> list[Order]:
    """Gets all orders for a given user."""
    return find_orders_by_user(user_id)


def serialize_order(order: Order) -> dict:
    """Serializes an order to a JSON-compatible dict."""
    # Get order items from database
    order_items = find_order_items(order.id)

    return {
        "order_id": order.id,
        "restaurant_id": order.restaurant_id,
        "user_id": order.user_id,
        "total": str(order.total),
        "delivery_fee": str(order.delivery_fee),
        "delivery_address": order.delivery_address,
        "tip": str(order.tip),
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


def serialize_orders(orders: list[Order]) -> list[dict]:
    """Serializes a list of orders to JSON-compatible dicts."""
    return [serialize_order(order) for order in orders]


def find_order_owner(order_id: int | str) -> int | None:
    """Finds the owner of an order."""
    order = find_order_by_id(order_id)
    if not order:
        logger.warning(f"Order not found: {order_id}")
        return None
    return order.user_id


# ============================================================
# CART SERVICES
# ============================================================
def create_cart(restaurant_id: int, user_id: int) -> Cart:
    """Creates and persists a new empty cart."""
    new_cart = Cart(restaurant_id=restaurant_id, user_id=user_id)
    save_cart(new_cart)
    logger.debug(f"Cart created: {new_cart.id} for user {user_id}")
    return new_cart


def add_item_to_cart(cart_id: int | str, item_id: int | str) -> Cart | None:
    """Adds an item to a cart."""
    cart = find_cart_by_id(cart_id)
    if not cart:
        logger.warning(f"Cart not found: {cart_id}")
        return None

    menu_item = find_menu_item_by_id(item_id)
    if not menu_item:
        raise CheekyApiError(f"Menu item not found: {item_id}")

    # Authorization check: user must be the owner of the cart
    if cart.user_id != g.user_id:
        raise CheekyApiError(f"User {g.user_id} is not the owner of cart {cart_id}")

    # Integrity check: menu item must be available
    if not menu_item.available:
        raise CheekyApiError(f"Menu item {item_id} is not available")

    # Integrity check: menu item must belong to the same restaurant as the cart
    if menu_item.restaurant_id != cart.restaurant_id:
        raise CheekyApiError(
            f"Menu item {item_id} does not belong to restaurant {cart.restaurant_id}"
        )

    # Integrity check: cart must be active
    if not cart.active:
        raise CheekyApiError(f"Cart {cart_id} is not active")

    add_cart_item(cart_id, item_id)
    logger.debug(f"Item {item_id} added to cart {cart_id}")
    return cart


def serialize_cart(cart: Cart) -> dict:
    """Serializes a cart to a JSON-compatible dict."""
    cart_items = get_cart_items(cart.id)
    return {
        "cart_id": cart.id,
        "restaurant_id": cart.restaurant_id,
        "items": [item.item_id for item in cart_items],
    }


# ============================================================
# REFUND SERVICES
# ============================================================
def create_refund(order_id: int, amount: Decimal, reason: str, auto_approved: bool) -> Refund:
    """Creates a new refund with a generated ID."""
    status = RefundStatus.approved if auto_approved else RefundStatus.pending
    refund = Refund(
        order_id=order_id,
        amount=amount,
        reason=reason,
        status=status,
        auto_approved=auto_approved,
    )
    save_refund(refund)
    return refund


def process_refund(refund: Refund, user_id: int) -> None:
    """Processes a refund: saves it and credits user if auto-approved."""
    if refund.status == RefundStatus.approved and not refund.paid:
        refund_user(user_id, refund.amount)
        refund.paid = True
        logger.info(f"Approved refund processed: {refund.id} of {refund.amount} for {user_id}")
    else:
        logger.error(
            f"Refund status: {refund.status}. Refund of {refund.amount} for {user_id} is not paid."
        )
    save_refund(refund)


def serialize_refund(refund: Refund) -> dict:
    """Serializes a refund to a JSON-compatible dict."""
    return {
        "refund_id": refund.id,
        "order_id": refund.order_id,
        "amount": str(refund.amount),
        "reason": refund.reason,
        "status": refund.status.value,  # Enum value
        "auto_approved": refund.auto_approved,
        "paid": refund.paid,
        "created_at": refund.created_at.isoformat(),
    }


def update_order_refund_status(
    order_id: int | str, status: Literal["approved", "rejected"]
) -> Refund | None:
    """Updates the status of a refund in the database."""
    refund = get_refund_by_order_id(order_id)
    if refund:
        # Integrity check: refunds are adjustable ONLY while in `pending` state
        if refund.status != RefundStatus.pending:
            raise CheekyApiError("Refund is not in pending state anymore")

        refund.status = RefundStatus.approved if status == "approved" else RefundStatus.rejected
        refund_owner = find_order_owner(order_id)
        if refund_owner is not None:
            process_refund(refund, refund_owner)
            return refund
        logger.warning(f"Unable to find owner for order {order_id}")
        return None
    logger.warning(f"Refund not found for order {order_id}")
    return None


# ============================================================
# PAYMENT SERVICES
# ============================================================
def charge_user(user_id: int, amount: Decimal) -> bool:
    """
    Charges a user, raises an exception if insufficient funds.
    Returns True if charged successfully, False if already charged.
    """
    user = find_user_by_id(user_id)
    if not user:
        raise ValueError(f"User '{user_id}' not found.")
    if user.balance < amount:
        raise ValueError("Insufficient funds.")

    # Charge the user
    user.balance -= amount
    save_user(user)
    logger.info(f"User charged: {user_id} - {amount}")
    return True


def refund_user(user_id: int, amount: Decimal) -> None:
    """Refunds a user by adding the amount back to their balance."""
    user = find_user_by_id(user_id)
    if not user:
        logger.error(f"Cannot refund - user not found: {user_id}")
        return

    user.balance += amount
    save_user(user)
    logger.info(f"User refunded: {user_id} + {amount}")
