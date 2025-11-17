"""
Repository Layer - Direct Database Access Only

This is the ONLY file that should import from storage.py and directly access the db dict.
All database operations should go through these repository functions.
When migrating to SQLAlchemy, only this file will need significant changes.
"""

import logging
from decimal import Decimal

from .models import Cart, MenuItem, Order, Refund, User
from .storage import db

logger = logging.getLogger(__name__)


# ============================================================
# MENU ITEMS
# ============================================================
def find_menu_item_by_id(item_id: str) -> MenuItem | None:
    """Finds a menu item by ID."""
    return db["menu_items"].get(item_id)


def find_all_menu_items() -> list[MenuItem]:
    """Gets all menu items."""
    return list(db["menu_items"].values())


# ============================================================
# USERS
# ============================================================
def find_user_by_id(user_id: str) -> User | None:
    """Finds a user by their user ID (email)."""
    return db["users"].get(user_id)


def save_user(user: User) -> None:
    """Saves a user to the database."""
    db["users"][user.user_id] = user


def increment_user_balance(user_id: str, amount: Decimal) -> Decimal | None:
    """Increments a user's balance."""
    user = find_user_by_id(user_id)
    logger.info(f"User: {user}, Amount: {amount}")
    if user:
        user.balance += amount
        logger.info(f"User: {user}, New Balance: {user.balance}")
        return user.balance
    return None


# ============================================================
# ORDERS
# ============================================================
def find_order_by_id(order_id: str) -> Order | None:
    """Finds an order by its ID."""
    return db["orders"].get(order_id)


def find_all_orders() -> list[Order]:
    """Gets all orders."""
    return list(db["orders"].values())


def save_order(order: Order) -> None:
    """Saves an order to the database."""
    db["orders"][order.order_id] = order


def delete_order(order_id: str) -> None:
    """Deletes an order from the database."""
    db["orders"].pop(order_id, None)


def generate_next_order_id() -> str:
    """Generates the next order ID based on existing orders."""
    return str(len(db["orders"]) + 1)


# ============================================================
# CARTS
# ============================================================
def find_cart_by_id(cart_id: str) -> Cart | None:
    """Finds a cart by its ID."""
    return db["carts"].get(cart_id)


def save_cart(cart: Cart) -> None:
    """Saves a cart to the database."""
    db["carts"][cart.cart_id] = cart


def generate_next_cart_id() -> str:
    """Generates the next cart ID based on existing carts."""
    return str(len(db["carts"]) + 1)


# ============================================================
# REFUNDS
# ============================================================
def save_refund(refund: Refund) -> None:
    """Saves a refund to the database."""
    db["refunds"][refund.refund_id] = refund


def generate_next_refund_id() -> str:
    """Generates the next refund ID based on existing refunds."""
    return str(len(db["refunds"]) + 1)


def get_refund_by_order_id(order_id: str) -> Refund | None:
    """Gets a refund by its order ID."""
    refunds = [refund for refund in db["refunds"].values() if refund.order_id == order_id]
    if refunds:
        return refunds[0]
    return None


# ============================================================
# CONFIGURATION
# ============================================================
def get_restaurant_api_key() -> str:
    """Gets the restaurant's API key from the database."""
    return db["restaurant_api_key"]


def get_platform_api_key() -> str:
    """Gets the platform's API key from the database."""
    return db["platform_api_key"]


def get_signup_bonus_remaining() -> Decimal:
    """Gets the remaining signup bonus amount."""
    return db["signup_bonus_remaining"]


def set_signup_bonus_remaining(amount: Decimal) -> None:
    """Sets the remaining signup bonus amount."""
    db["signup_bonus_remaining"] = amount
