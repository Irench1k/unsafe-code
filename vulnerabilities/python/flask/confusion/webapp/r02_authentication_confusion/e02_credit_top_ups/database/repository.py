"""
Repository Layer - Direct Database Access Only

This is the ONLY file that should import from storage.py and directly access the db dict.
All database operations should go through these repository functions.
When migrating to SQLAlchemy, only this file will need significant changes.
"""

from decimal import Decimal
from .models import Cart, MenuItem, Order, Refund, User
from .storage import db


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


def user_exists(user_id: str) -> bool:
    """Checks if a user exists in the database."""
    return user_id in db["users"]


def save_user(user: User) -> None:
    """Saves a user to the database."""
    db["users"][user.user_id] = user


def increment_user_balance(user_id: str, amount: Decimal) -> Decimal | None:
    """Increments a user's balance."""
    user = find_user_by_id(user_id)
    print(f"User: {user}, Amount: {amount}")
    if user:
        user.balance += amount
        print(f"User: {user}, New Balance: {user.balance}")
        return user.balance
    return None


# ============================================================
# ORDERS
# ============================================================
def find_order_by_id(order_id: str) -> Order | None:
    """Finds an order by its ID."""
    return db["orders"].get(order_id)


def order_exists(order_id: str) -> bool:
    """Checks if an order exists."""
    return order_id in db["orders"]


def find_all_orders() -> list[Order]:
    """Gets all orders."""
    return list(db["orders"].values())


def save_order(order: Order) -> None:
    """Saves an order to the database."""
    db["orders"][order.order_id] = order


def delete_order(order_id: str) -> None:
    """Deletes an order from the database."""
    db["orders"].pop(order_id, None)


def get_and_increment_order_id() -> str:
    """Gets the next order ID and increments the counter atomically."""
    reserved_order_id = str(db["next_order_id"])
    db["next_order_id"] += 1
    return reserved_order_id


# ============================================================
# CARTS
# ============================================================
def find_cart_by_id(cart_id: str) -> Cart | None:
    """Finds a cart by its ID."""
    return db["carts"].get(cart_id)


def save_cart(cart: Cart) -> None:
    """Saves a cart to the database."""
    db["carts"][cart.cart_id] = cart


def get_and_increment_cart_id() -> str:
    """Gets the next cart ID and increments the counter atomically."""
    reserved_cart_id = str(db["next_cart_id"])
    db["next_cart_id"] += 1
    return reserved_cart_id


# ============================================================
# REFUNDS
# ============================================================
def save_refund(refund: Refund) -> None:
    """Saves a refund to the database."""
    db["refunds"][refund.refund_id] = refund


def get_and_increment_refund_id() -> str:
    """Gets the next refund ID and increments the counter atomically."""
    reserved_refund_id = str(db["next_refund_id"])
    db["next_refund_id"] += 1
    return reserved_refund_id


# ============================================================
# CONFIGURATION
# ============================================================
def get_api_key() -> str:
    """Gets the restaurant's API key from the database."""
    return db["restaurant_api_key"]


def get_platform_api_key() -> str:
    """Gets the platform's API key from the database."""
    return db["platform_api_key"]


def get_signup_bonus_remaining():
    """Gets the remaining signup bonus amount."""
    return db["signup_bonus_remaining"]


def decrement_signup_bonus(amount) -> None:
    """Decrements the signup bonus remaining."""
    db["signup_bonus_remaining"] -= amount
