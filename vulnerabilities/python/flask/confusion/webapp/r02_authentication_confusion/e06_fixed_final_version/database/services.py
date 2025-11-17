"""
Business Logic Layer

Contains high-level business operations that coordinate multiple repository calls
and enforce business rules. No direct database access - all operations go through
the repository.
"""

import logging
from decimal import Decimal
from typing import Literal

from flask import g

from ..errors import CheekyApiError
from .models import Cart, Order, Refund, User
from .repository import (
    delete_order,
    find_all_orders,
    find_cart_by_id,
    find_order_by_id,
    find_menu_item_by_id,
    find_user_by_id,
    generate_next_cart_id,
    generate_next_order_id,
    generate_next_refund_id,
    get_refund_by_order_id,
    get_signup_bonus_remaining,
    save_cart,
    save_order,
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
    return [item.model_dump() for item in menu_items]


# ============================================================
# USER SERVICES
# ============================================================
def create_user(email: str, password: str, name: str) -> None:
    """Creates a new user."""
    user = User(user_id=email, name=name, password=password)
    save_user(user)
    logger.info(f"User created: {email}")


def apply_signup_bonus(email: str) -> None:
    """Applies a signup bonus to a newly registered user."""
    user = find_user_by_id(email)
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


def increment_user_balance(user_id: str, amount: Decimal) -> Decimal | None:
    """Increments a user's balance and returns the new balance."""
    user = find_user_by_id(user_id)
    if not user:
        logger.warning(f"Cannot increment balance - user not found: {user_id}")
        return None

    user.balance += amount
    save_user(user)
    logger.info(f"Balance updated for {user_id}: +{amount} = {user.balance}")
    return user.balance


def get_current_user(email: str) -> User | None:
    """Gets the current user from the database."""
    user_email = email or getattr(g, "email", None)
    if not user_email:
        logger.warning("No email provided and no user in request context")
        return None

    return find_user_by_id(user_email)


# ============================================================
# ORDER SERVICES
# ============================================================
def create_order_from_checkout(
    user_id: str,
    total: Decimal,
    items: list,
    delivery_fee: Decimal,
    delivery_address: str,
    tip: Decimal = Decimal("0.00"),
) -> Order:
    """Creates a new order with a generated ID."""
    order_id = generate_next_order_id()
    return Order(
        order_id=order_id,
        user_id=user_id,
        total=total,
        items=items,
        delivery_fee=delivery_fee,
        delivery_address=delivery_address,
        tip=tip,
    )


def save_order_securely(order: Order) -> None:
    """
    Charge customer and save order in DB, now with idempotency & rollback!

    This is a transactional operation that ensures data consistency:
    - Charges the user
    - Saves the order
    - Rolls back both operations if anything fails
    """
    charged_successfully = False

    try:
        charged_successfully = charge_user(order.user_id, order.total, order.order_id)
        save_order(order)
        logger.info(f"Order saved: {order.order_id} for user {order.user_id}")
    except Exception as e:
        logger.error(f"Order save failed: {order.order_id} - {e}")
        # Rollback routine: refund the customer if we charged them + remove the order from the database
        if charged_successfully:
            refund_user(order.user_id, order.total)

        # Remove the order from the database
        delete_order(order.order_id)
        raise


def get_user_orders(user_id: str) -> list[Order]:
    """Gets all orders for a given user."""
    return [order for order in find_all_orders() if order.user_id == user_id]


def serialize_order(order: Order) -> dict:
    """Serializes an order to a JSON-compatible dict."""
    return order.model_dump(mode="json")


def serialize_orders(orders: list[Order]) -> list[dict]:
    """Serializes a list of orders to JSON-compatible dicts."""
    return [serialize_order(order) for order in orders]


def find_order_owner(order_id: str) -> str:
    """Finds the owner of an order."""
    order = find_order_by_id(order_id)
    if not order:
        logger.warning(f"Order not found: {order_id}")
        return None
    return order.user_id


# ============================================================
# CART SERVICES
# ============================================================
def create_cart(user_id: str) -> Cart:
    """Creates and persists a new empty cart tied to the user."""
    cart_id = generate_next_cart_id()
    new_cart = Cart(cart_id=cart_id, user_id=user_id, items=[], active=True)
    save_cart(new_cart)
    logger.debug(f"Cart created: {cart_id}")
    return new_cart


def add_item_to_cart(cart_id: str, item_id: str, user_id: str) -> Cart:
    """Adds an item to a cart with ownership and availability checks."""
    cart = find_cart_by_id(cart_id)
    if not cart:
        logger.warning(f"Cart not found: {cart_id}")
        raise CheekyApiError("Cart not found")

    if cart.user_id != user_id:
        logger.warning(f"Cart {cart_id} ownership mismatch for {user_id}")
        raise CheekyApiError("Cart does not belong to user")

    if not cart.active:
        raise CheekyApiError("Cart is no longer active")

    menu_item = find_menu_item_by_id(item_id)
    if not menu_item or not menu_item.available:
        raise CheekyApiError("Menu item is unavailable")

    cart.items.append(item_id)
    save_cart(cart)
    logger.debug(f"Item {item_id} added to cart {cart_id}")
    return cart


def serialize_cart(cart: Cart) -> dict:
    """Serializes a cart to a JSON-compatible dict."""
    return cart.model_dump()


# ============================================================
# REFUND SERVICES
# ============================================================
def create_refund(order_id: str, amount: Decimal, reason: str, auto_approved: bool) -> Refund:
    """Creates a new refund with a generated ID."""
    refund_id = generate_next_refund_id()
    status = "auto_approved" if auto_approved else "pending"
    return Refund(
        refund_id=refund_id,
        order_id=order_id,
        amount=amount,
        reason=reason,
        status=status,
        auto_approved=auto_approved,
    )


def process_refund(refund: Refund, user_id: str) -> None:
    """Processes a refund: saves it and credits user if auto-approved."""
    if refund.status in ("auto_approved", "approved") and not refund.paid:
        refund_user(user_id, refund.amount)
        refund.paid = True
        logger.info(
            f"Approved refund processed: {refund.refund_id} of {refund.amount} for {user_id}"
        )
    else:
        logger.error(
            f"Refund status: {refund.status}. Refund of {refund.amount} for {user_id} is not paid."
        )

    save_refund(refund)

    # Mark the order as refunded once money is returned to the user
    if refund.paid:
        order = find_order_by_id(refund.order_id)
        if order:
            order.refunded = True
            save_order(order)


def serialize_refund(refund: Refund) -> dict:
    """Serializes a refund to a JSON-compatible dict."""
    return refund.model_dump(mode="json")


def update_order_refund_status(
    order_id: str, status: Literal["approved", "rejected"]
) -> Refund | None:
    """Updates the status of a refund in the database."""
    refund = get_refund_by_order_id(order_id)
    if refund:
        if refund.status != "pending":
            raise CheekyApiError("Refund status can only be changed from pending")

        refund.status = status
        refund_owner = find_order_owner(order_id)
        process_refund(refund, refund_owner)
        return refund
    logger.warning(f"Refund not found for order {order_id}")
    return None


# ============================================================
# PAYMENT SERVICES
# ============================================================
def charge_user(user_id: str, amount: Decimal, order_id: str) -> bool:
    """
    Charges a user, raises an exception if insufficient funds.
    Returns True if charged successfully, False if already charged.
    """
    user = find_user_by_id(user_id)
    if not user:
        raise ValueError(f"User '{user_id}' not found.")
    if user.balance < amount:
        raise ValueError("Insufficient funds.")

    # Don't charge the user twice for the same order (idempotency check)
    existing_order = find_order_by_id(order_id)
    if existing_order and existing_order.user_id == user_id:
        logger.info(f"Order already exists, skipping charge: {order_id}")
        return False

    # Charge the user
    user.balance -= amount
    save_user(user)
    logger.info(f"User charged: {user_id} - {amount}")
    return True


def refund_user(user_id: str, amount: Decimal) -> None:
    """Refunds a user by adding the amount back to their balance."""
    user = find_user_by_id(user_id)
    if not user:
        logger.error(f"Cannot refund - user not found: {user_id}")
        return

    user.balance += amount
    save_user(user)
    logger.info(f"User refunded: {user_id} + {amount}")
