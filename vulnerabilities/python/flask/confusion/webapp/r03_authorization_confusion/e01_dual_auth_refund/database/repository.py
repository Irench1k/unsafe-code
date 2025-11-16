"""
Repository Layer - Database Access Only

This is the ONLY file (besides db.py) that should directly interact with
the database. All database operations should go through these repository functions.

The repository uses SQLAlchemy ORM and expects a session to be available
in Flask's g object (set up by middleware).
"""

import logging
from decimal import Decimal

from flask import g
from sqlalchemy import select

from .models import (
    Cart,
    CartItem,
    MenuItem,
    Order,
    OrderItem,
    PlatformConfig,
    Refund,
    Restaurant,
    User,
)

logger = logging.getLogger(__name__)


def get_session():
    """Get the current database session from Flask's g object."""
    if not hasattr(g, "db_session"):
        raise RuntimeError("No database session available. Did you forget to set up middleware?")
    return g.db_session


# ============================================================
# RESTAURANTS
# ============================================================
def find_all_restaurants() -> list[Restaurant]:
    """Gets all restaurants."""
    session = get_session()
    return list(session.execute(select(Restaurant)).scalars().all())


def find_restaurant_by_id(restaurant_id: str) -> Restaurant | None:
    """Finds a restaurant by ID."""
    session = get_session()
    return session.get(Restaurant, restaurant_id)


def find_restaurant_by_api_key(api_key: str) -> Restaurant | None:
    """Finds a restaurant by API key."""
    session = get_session()
    stmt = select(Restaurant).where(Restaurant.api_key == api_key)
    return session.execute(stmt).scalar_one_or_none()


# ============================================================
# MENU ITEMS
# ============================================================
def find_menu_item_by_id(item_id: str) -> MenuItem | None:
    """Finds a menu item by ID."""
    session = get_session()
    return session.get(MenuItem, item_id)


def find_all_menu_items() -> list[MenuItem]:
    """Gets all menu items."""
    session = get_session()
    return list(session.execute(select(MenuItem)).scalars().all())


def find_menu_items_by_restaurant(restaurant_id: str) -> list[MenuItem]:
    """Gets all menu items for a specific restaurant."""
    session = get_session()
    stmt = select(MenuItem).where(MenuItem.restaurant_id == restaurant_id)
    return list(session.execute(stmt).scalars().all())


# ============================================================
# USERS
# ============================================================
def find_user_by_id(user_id: str) -> User | None:
    """Finds a user by their user ID (email)."""
    session = get_session()
    return session.get(User, user_id)


def save_user(user: User) -> None:
    """Saves a user to the database."""
    session = get_session()
    session.add(user)
    session.commit()


def increment_user_balance(user_id: str, amount: Decimal) -> Decimal | None:
    """Increments a user's balance."""
    user = find_user_by_id(user_id)
    logger.info(f"User: {user}, Amount: {amount}")
    if user:
        user.balance += amount
        session = get_session()
        session.commit()
        logger.info(f"User: {user}, New Balance: {user.balance}")
        return user.balance
    return None


# ============================================================
# ORDERS
# ============================================================
def find_order_by_id(order_id: str) -> Order | None:
    """Finds an order by its ID."""
    session = get_session()
    return session.get(Order, order_id)


def find_all_orders() -> list[Order]:
    """Gets all orders."""
    session = get_session()
    return list(session.execute(select(Order)).scalars().all())


def find_orders_by_user(user_id: str) -> list[Order]:
    """Gets all orders for a specific user."""
    session = get_session()
    stmt = select(Order).where(Order.user_id == user_id)
    return list(session.execute(stmt).scalars().all())


def find_orders_by_restaurant(restaurant_id: str) -> list[Order]:
    """Gets all orders for a specific restaurant."""
    session = get_session()
    stmt = select(Order).where(Order.restaurant_id == restaurant_id)
    return list(session.execute(stmt).scalars().all())


def save_order(order: Order) -> None:
    """Saves an order to the database."""
    session = get_session()
    session.add(order)
    session.commit()


def delete_order(order_id: str) -> None:
    """Deletes an order from the database."""
    session = get_session()
    order = session.get(Order, order_id)
    if order:
        # Also delete associated order items
        stmt = select(OrderItem).where(OrderItem.order_id == order_id)
        order_items = session.execute(stmt).scalars().all()
        for item in order_items:
            session.delete(item)
        session.delete(order)
        session.commit()


def generate_next_order_id() -> str:
    """Generates the next order ID based on existing orders."""
    session = get_session()
    stmt = select(Order)
    order_count = len(list(session.execute(stmt).scalars().all()))
    return str(order_count + 1)


def find_order_items(order_id: str) -> list[OrderItem]:
    """Gets all items for a specific order."""
    session = get_session()
    stmt = select(OrderItem).where(OrderItem.order_id == order_id)
    return list(session.execute(stmt).scalars().all())


def save_order_items(order_items: list[OrderItem]) -> None:
    """Saves order items to the database."""
    session = get_session()
    for item in order_items:
        session.add(item)
    session.commit()


# ============================================================
# CARTS
# ============================================================
def find_cart_by_id(cart_id: str) -> Cart | None:
    """Finds a cart by its ID."""
    session = get_session()
    return session.get(Cart, cart_id)


def get_cart_items(cart_id: str) -> list[str]:
    """Gets all item IDs for a specific cart."""
    session = get_session()
    stmt = select(CartItem).where(CartItem.cart_id == cart_id)
    cart_items = session.execute(stmt).scalars().all()
    return [item.item_id for item in cart_items]


def save_cart(cart: Cart) -> None:
    """Saves a cart to the database."""
    session = get_session()
    session.add(cart)
    session.commit()


def add_cart_item(cart_id: str, item_id: str) -> None:
    """Adds an item to a cart."""
    session = get_session()
    cart_item = CartItem(cart_id=cart_id, item_id=item_id)
    session.add(cart_item)
    session.commit()


def generate_next_cart_id() -> str:
    """Generates the next cart ID based on existing carts."""
    session = get_session()
    stmt = select(Cart)
    cart_count = len(list(session.execute(stmt).scalars().all()))
    return str(cart_count + 1)


# ============================================================
# REFUNDS
# ============================================================
def save_refund(refund: Refund) -> None:
    """Saves a refund to the database."""
    session = get_session()
    session.add(refund)
    session.commit()


def generate_next_refund_id() -> str:
    """Generates the next refund ID based on existing refunds."""
    session = get_session()
    stmt = select(Refund)
    refund_count = len(list(session.execute(stmt).scalars().all()))
    return str(refund_count + 1)


def get_refund_by_order_id(order_id: str) -> Refund | None:
    """Gets a refund by its order ID."""
    session = get_session()
    stmt = select(Refund).where(Refund.order_id == order_id)
    return session.execute(stmt).scalar_one_or_none()


# ============================================================
# CONFIGURATION
# ============================================================
def get_restaurant_api_key() -> str:
    """
    Gets the restaurant's API key from the database.

    DEPRECATED: Use find_restaurant_by_api_key() instead for multi-tenancy.
    This function returns the first restaurant's API key for backward compatibility.
    """
    restaurants = find_all_restaurants()
    if restaurants:
        return restaurants[0].api_key
    raise ValueError("No restaurants found in database")


def get_platform_api_key() -> str:
    """Gets the platform's API key from the database."""
    session = get_session()
    config = session.get(PlatformConfig, "platform_api_key")
    if config:
        return config.value
    raise ValueError("Platform API key not found in database")


def get_signup_bonus_remaining() -> Decimal:
    """Gets the remaining signup bonus amount."""
    session = get_session()
    config = session.get(PlatformConfig, "signup_bonus_remaining")
    if config:
        return Decimal(config.value)
    return Decimal("0.00")


def set_signup_bonus_remaining(amount: Decimal) -> None:
    """Sets the remaining signup bonus amount."""
    session = get_session()
    config = session.get(PlatformConfig, "signup_bonus_remaining")
    if config:
        config.value = str(amount)
    else:
        config = PlatformConfig(key="signup_bonus_remaining", value=str(amount))
        session.add(config)
    session.commit()
