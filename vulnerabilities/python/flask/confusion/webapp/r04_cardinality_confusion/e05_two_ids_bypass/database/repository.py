"""
Repository Layer - Database Access Only

This is the ONLY file (besides db.py) that should directly interact with
the database. All database operations should go through these repository functions.

v405 Conventions:
-----------------
- Query patterns:
  - By PK: session.get(Model, pk)
  - Single by field: session.execute(select(...)).scalar_one_or_none()
  - Lists: session.scalars(select(...)).all()

- Write patterns:
  - Create: construct model, session.add(), session.flush()
  - Update (partial): fetch model, modify non-None attrs, session.flush()
  - Update (bulk): session.execute(update(...).values({...})), session.flush()

- Always flush() after writes to materialize changes
- Never commit() - handled by request middleware
- Type validation belongs in validators, not here
"""

import logging
from decimal import Decimal

from flask import g
from sqlalchemy import select

from ..auth.helpers import get_trusted_restaurant_id
from .models import (
    Cart,
    CartItem,
    Coupon,
    MenuItem,
    Order,
    OrderItem,
    PlatformConfig,
    Refund,
    Restaurant,
    User,
)

logger = logging.getLogger(__name__)


def _session():
    """Return the request-scoped session."""
    if not hasattr(g, "db_session"):
        raise RuntimeError("No database session available")
    return g.db_session


# ============================================================
# RESTAURANTS
# ============================================================
def get_trusted_restaurant() -> Restaurant | None:
    """Get the restaurant for the current request context."""
    restaurant_id = get_trusted_restaurant_id()
    if restaurant_id is None:
        return None
    return _session().get(Restaurant, restaurant_id)


def find_all_restaurants() -> list[Restaurant]:
    """Get all restaurants."""
    return _session().scalars(select(Restaurant)).all()


def find_restaurant_by_id(restaurant_id: int) -> Restaurant | None:
    """Find a restaurant by ID."""
    return _session().get(Restaurant, restaurant_id)


def find_restaurant_by_domain(domain: str) -> Restaurant | None:
    """Find a restaurant by domain."""
    return _session().execute(
        select(Restaurant).where(Restaurant.domain == domain)
    ).scalar_one_or_none()


def find_restaurant_by_api_key(api_key: str) -> Restaurant | None:
    """Find a restaurant by API key."""
    return _session().execute(
        select(Restaurant).where(Restaurant.api_key == api_key)
    ).scalar_one_or_none()


def find_restaurant_users() -> list[User]:
    """Users associated with a restaurant (via email domain match)."""
    restaurant = get_trusted_restaurant()
    if not restaurant:
        return []
    return _session().scalars(
        select(User).where(User.email.endswith(f"@{restaurant.domain}"))
    ).all()


def create_restaurant(name: str, description: str, domain: str, owner: str) -> Restaurant:
    """Create a new restaurant."""
    import uuid

    restaurant = Restaurant(
        name=name,
        description=description,
        domain=domain,
        owner=owner,
        api_key=f"key-{domain.replace('.', '-')}-{uuid.uuid4()}",
    )
    _session().add(restaurant)
    _session().flush()
    return restaurant


def update_restaurant(
    name: str | None = None,
    description: str | None = None,
    domain: str | None = None,
) -> Restaurant | None:
    """Update the trusted restaurant (partial update - only non-None fields)."""
    restaurant = get_trusted_restaurant()
    if not restaurant:
        return None

    if name is not None:
        restaurant.name = name
    if description is not None:
        restaurant.description = description
    if domain is not None:
        restaurant.domain = domain

    _session().flush()
    return restaurant


# ============================================================
# MENU ITEMS
# ============================================================
def find_menu_item_by_id(item_id: int) -> MenuItem | None:
    """Find a menu item by ID (no tenant scoping)."""
    return _session().get(MenuItem, item_id)


def find_all_menu_items() -> list[MenuItem]:
    """Get all menu items (no tenant scoping)."""
    return _session().scalars(select(MenuItem)).all()


def find_restaurant_menu_items() -> list[MenuItem]:
    """Get all menu items for the trusted restaurant."""
    restaurant_id = get_trusted_restaurant_id()
    if restaurant_id is None:
        # No restaurant context - return all (public listing)
        return _session().scalars(select(MenuItem)).all()
    return _session().scalars(
        select(MenuItem).where(MenuItem.restaurant_id == restaurant_id)
    ).all()


def find_restaurant_menu_item(item_id: int) -> MenuItem | None:
    """Find a menu item verified to belong to the trusted restaurant."""
    restaurant_id = get_trusted_restaurant_id()
    return _session().execute(
        select(MenuItem)
        .where(MenuItem.id == item_id)
        .where(MenuItem.restaurant_id == restaurant_id)
    ).scalar_one_or_none()


def create_restaurant_menu_item(name: str, price: Decimal, available: bool | None = None) -> MenuItem:
    """Create a menu item for the trusted restaurant."""
    menu_item = MenuItem(
        restaurant_id=get_trusted_restaurant_id(),
        name=name,
        price=price,
        available=available if available is not None else True,
    )
    _session().add(menu_item)
    _session().flush()
    return menu_item


def update_restaurant_menu_item(
    item_id: int,
    name: str | None = None,
    price: Decimal | None = None,
    available: bool | None = None,
) -> MenuItem | None:
    """
    Update a menu item with tenant scoping (partial update).

    Only updates fields that are not None. Returns the updated item,
    or None if item doesn't exist or doesn't belong to trusted restaurant.

    @unsafe {
        "vuln_id": "v405",
        "severity": "high",
        "category": "cardinality-confusion",
        "description": "get_trusted_restaurant_id() consumes from request - second call returns different value",
        "cwe": "CWE-1289"
    }
    """
    restaurant_id = get_trusted_restaurant_id()

    # Find the item with tenant scoping
    menu_item = _session().execute(
        select(MenuItem)
        .where(MenuItem.id == item_id)
        .where(MenuItem.restaurant_id == restaurant_id)
    ).scalar_one_or_none()

    if not menu_item:
        return None

    # Partial update - only set non-None fields
    if name is not None:
        menu_item.name = name
    if price is not None:
        menu_item.price = price
    if available is not None:
        menu_item.available = available

    _session().flush()
    return menu_item


def reserve_if_available(item_id: int) -> bool:
    """Check if a menu item is available for reservation."""
    menu_item = find_menu_item_by_id(item_id)
    if not menu_item:
        return False
    return menu_item.available


# ============================================================
# COUPONS
# ============================================================
def find_coupon_by_id(coupon_id: int) -> Coupon | None:
    """Find a coupon by ID."""
    return _session().get(Coupon, coupon_id)


def find_all_coupons() -> list[Coupon]:
    """Get all coupons."""
    return _session().scalars(select(Coupon)).all()


def find_restaurant_coupons() -> list[Coupon]:
    """Get all coupons for the trusted restaurant."""
    restaurant_id = get_trusted_restaurant_id()
    return _session().scalars(
        select(Coupon).where(Coupon.restaurant_id == restaurant_id)
    ).all()


def find_coupon_by_code(coupon_code: str) -> Coupon | None:
    """Find a coupon by its code."""
    return _session().execute(
        select(Coupon).where(Coupon.code == f"CODE-{coupon_code.upper()}")
    ).scalar_one_or_none()


def save_coupon(coupon: Coupon) -> None:
    """Persist coupon changes."""
    _session().add(coupon)
    _session().flush()


# ============================================================
# USERS
# ============================================================
def find_user_by_id(user_id: int) -> User | None:
    """Find a user by ID."""
    return _session().get(User, user_id)


def find_user_by_email(email: str) -> User | None:
    """Find a user by email."""
    return _session().execute(
        select(User).where(User.email == email)
    ).scalar_one_or_none()


def save_user(user: User) -> None:
    """Persist a user."""
    _session().add(user)
    _session().flush()


def increment_user_balance(email: str, amount: Decimal) -> Decimal | None:
    """Increment a user's balance and return new balance."""
    user = find_user_by_email(email)
    if not user:
        return None
    user.balance += amount
    _session().flush()
    return user.balance


# ============================================================
# ORDERS
# ============================================================
def find_order_by_id(order_id: int) -> Order | None:
    """Find an order by ID."""
    return _session().get(Order, order_id)


def find_all_orders() -> list[Order]:
    """Get all orders."""
    return _session().scalars(select(Order)).all()


def find_orders_by_user(user_id: int) -> list[Order]:
    """Get all orders for a user."""
    return _session().scalars(
        select(Order).where(Order.user_id == user_id)
    ).all()


def find_restaurant_orders(
    order_ids: list[int] | None = None, restaurant_id: int | None = None
) -> list[Order]:
    """Get orders for a restaurant, optionally filtered by IDs.

    Args:
        order_ids: Optional list of order IDs to filter by
        restaurant_id: If provided, use this ID directly (v305 fix for body override).
                      If None, falls back to get_trusted_restaurant_id().
    """
    if restaurant_id is None:
        restaurant_id = get_trusted_restaurant_id()
    query = select(Order).where(Order.restaurant_id == restaurant_id)
    if order_ids:
        query = query.where(Order.id.in_(order_ids))
    return _session().scalars(query).all()


def save_order(order: Order) -> None:
    """Persist an order."""
    _session().add(order)
    _session().flush()


def delete_order(order_id: int) -> None:
    """Delete an order and its items."""
    order = _session().get(Order, order_id)
    if not order:
        return
    # Delete associated order items first
    for item in _session().scalars(select(OrderItem).where(OrderItem.order_id == order_id)).all():
        _session().delete(item)
    _session().delete(order)
    _session().flush()


def find_order_items(order_id: int) -> list[OrderItem]:
    """Get all items for an order."""
    return _session().scalars(
        select(OrderItem).where(OrderItem.order_id == order_id)
    ).all()


def save_order_items(order_items: list[OrderItem]) -> None:
    """Persist multiple order items."""
    for item in order_items:
        _session().add(item)
    _session().flush()


# ============================================================
# CARTS
# ============================================================
def find_cart_by_id(cart_id: int) -> Cart | None:
    """Find a cart by ID."""
    return _session().get(Cart, cart_id)


def find_cart_items(cart_id: int) -> list[CartItem]:
    """Get all items for a cart."""
    return _session().scalars(
        select(CartItem).where(CartItem.cart_id == cart_id)
    ).all()


def save_cart(cart: Cart) -> None:
    """Persist a cart."""
    _session().add(cart)
    _session().flush()


def create_cart_item(
    cart_id: int, item_id: int, name: str, price: Decimal, quantity: int = 1
) -> CartItem:
    """Create a cart item."""
    cart_item = CartItem(
        cart_id=cart_id,
        item_id=item_id,
        name=name,
        price=price,
        quantity=quantity,
    )
    _session().add(cart_item)
    _session().flush()
    return cart_item


def save_cart_item(cart_item: CartItem) -> None:
    """Persist a cart item."""
    _session().add(cart_item)
    _session().flush()


# ============================================================
# REFUNDS
# ============================================================
def save_refund(refund: Refund) -> None:
    """Persist a refund."""
    _session().add(refund)
    _session().flush()


def find_refund_by_order_id(order_id: int) -> Refund | None:
    """Find a refund by order ID."""
    return _session().execute(
        select(Refund).where(Refund.order_id == order_id)
    ).scalar_one_or_none()


def find_restaurant_refund_by_order_id(order_id: int) -> Refund | None:
    """Find a refund by order ID with tenant scoping."""
    return _session().execute(
        select(Refund)
        .join(Order, Refund.order_id == Order.id)
        .where(Refund.order_id == order_id)
        .where(Order.restaurant_id == get_trusted_restaurant_id())
    ).scalar_one_or_none()


def find_restaurant_refunds() -> list[Refund]:
    """Get all refunds for the trusted restaurant's orders."""
    return _session().scalars(
        select(Refund)
        .join(Order, Refund.order_id == Order.id)
        .where(Order.restaurant_id == get_trusted_restaurant_id())
    ).all()


# ============================================================
# CONFIGURATION
# ============================================================
def get_platform_api_key() -> str:
    """Get the platform's API key."""
    config = _find_platform_config("platform_api_key")
    if config:
        return config.value
    raise ValueError("Platform API key not found in database")


def get_signup_bonus_remaining() -> Decimal:
    """Get the remaining signup bonus amount."""
    config = _find_platform_config("signup_bonus_remaining")
    if config:
        return Decimal(config.value)
    return Decimal("0.00")


def set_signup_bonus_remaining(amount: Decimal) -> None:
    """Set the remaining signup bonus amount."""
    config = _find_platform_config("signup_bonus_remaining")
    if config:
        config.value = str(amount)
    else:
        config = PlatformConfig(key="signup_bonus_remaining", value=str(amount))
        _session().add(config)
    _session().flush()


def _find_platform_config(key: str) -> PlatformConfig | None:
    """Find a platform config entry by key."""
    return _session().execute(
        select(PlatformConfig).where(PlatformConfig.key == key)
    ).scalar_one_or_none()
