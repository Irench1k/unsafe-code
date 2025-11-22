"""
Business Logic Layer

Contains high-level business operations that coordinate multiple repository calls
and enforce business rules. No direct database access - all operations go through
the repository.
"""

from decimal import Decimal

from flask import g

from .models import Cart, Order, User
from .repository import (
    decrement_signup_bonus,
    delete_order,
    find_all_orders,
    find_cart_by_id,
    find_order_by_id,
    find_user_by_id,
    get_and_increment_cart_id,
    get_signup_bonus_remaining,
    order_exists,
    reset_database,
    save_cart,
    save_order,
    save_user,
    set_user_balance,
)


# ============================================================
# USER SERVICES
# ============================================================
def create_user(email: str, password: str, name: str) -> None:
    """Creates a new user."""
    user = User(user_id=email, name=name, password=password)
    save_user(user)


def apply_signup_bonus(email: str) -> None:
    """Applies a signup bonus to a newly registered user."""
    user = find_user_by_id(email)
    if not user:
        return

    bonus_amount = Decimal("2.00")
    decrement_signup_bonus(bonus_amount)

    if get_signup_bonus_remaining() < Decimal("0.00"):
        print(f"No signup bonus remaining to apply to user '{email}'.")
        return

    user.balance += bonus_amount


def get_current_user() -> User | None:
    """Gets the current user from the database."""
    return find_user_by_id(g.email)


# ============================================================
# ORDER SERVICES
# ============================================================
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
    except Exception:
        # Rollback routine: refund the customer if we charged them + remove the order from the database
        if charged_successfully:
            refund_user(order.user_id, order.total)

        # Remove the order from the database
        delete_order(order.order_id)


def get_user_orders(user_id: str) -> list[Order]:
    """Gets all orders for a given user."""
    orders = []
    for order in find_all_orders():
        if order.user_id == user_id:
            orders.append(order)
    return orders


# ============================================================
# CART SERVICES
# ============================================================
def create_cart() -> Cart:
    """Creates and persists a new empty cart."""
    cart_id = get_and_increment_cart_id()
    new_cart = Cart(cart_id=cart_id, items=[])
    save_cart(new_cart)
    return new_cart


def add_item_to_cart(cart_id: str, item_id: str) -> Cart | None:
    """Adds an item to a cart."""
    cart = find_cart_by_id(cart_id)
    if not cart:
        return None

    cart.items.append(item_id)
    return cart


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
    if order_exists(order_id):
        existing_order = find_order_by_id(order_id)
        if existing_order and existing_order.user_id == user_id:
            return False

    # Charge the user
    user.balance -= amount
    return True


# ============================================================
# PLATFORM UTILITIES (test determinism)
# ============================================================
def reset_for_tests():
    reset_database()


def set_balance_for_tests(user_id: str, amount: Decimal) -> bool:
    return set_user_balance(user_id, amount)


def refund_user(user_id: str, amount: Decimal) -> None:
    """Refunds a user by adding the amount back to their balance."""
    user = find_user_by_id(user_id)
    if user:
        user.balance += amount
