from decimal import Decimal

from .models import Cart, MenuItem, Order, OrderItem, User
from .storage import db

# ============================================================
# DATA ACCESS LAYER
# This layer is responsible for accessing the data from the database.
# The layering right now isn't very strict, will improve on this in the future.
# ============================================================


# utils.py
def get_menu_item(item_id: str) -> MenuItem | None:
    return db["menu_items"].get(item_id)


# auth.py
def get_user(user_id: str) -> User | None:
    """Gets a User by their user ID."""
    return db["users"].get(user_id)


# auth.py
def get_api_key() -> str:
    """Gets the restaurant's API key from the database."""
    return db["api_key"]


def _save_order_securely(order: Order):
    """Charge customer and save order in DB, now with idempotency & rollback!"""
    charged_successfully = False

    try:
        charged_successfully = charge_user(order.user_id, order.total, order.order_id)
        db["orders"][order.order_id] = order
    except Exception:
        # Rollback routine: refund the customer if we charged them + remove the order from the database
        if charged_successfully:
            refund_user(order.user_id, order.total)

        # Remove the order from the database
        db["orders"].pop(order.order_id, None)


def get_next_order_id() -> str:
    """Gets the next order ID and increments the counter."""
    reserved_order_id = str(db["next_order_id"])
    db["next_order_id"] += 1
    return reserved_order_id


# routes.py
def get_all_orders() -> list[Order]:
    """Gets all orders."""
    return list(db["orders"].values())


# routes.py
def get_all_menu_items() -> list[MenuItem]:
    """Gets all menu items."""
    return list(db["menu_items"].values())


def _get_next_cart_id() -> str:
    """Gets the next cart ID and increments the counter."""
    reserved_cart_id = str(db["next_cart_id"])
    db["next_cart_id"] += 1
    return reserved_cart_id


def _create_cart(cart: Cart):
    """Creates a new cart in the database."""
    db["carts"][cart.cart_id] = cart


# routes.py
def get_cart(cart_id: str) -> Cart | None:
    """Gets a cart by its ID."""
    return db["carts"].get(cart_id)


# ============================================================
# BUSINESS LOGIC
# High-level business logic for the application.
# ============================================================
def charge_user(user_id: str, amount: Decimal, order_id: str) -> bool:
    """Charges a user, raises an exception if insufficient funds, returns True if charged sucessfully."""
    # The exception signals that we shouldn't proceed with the order!
    user = get_user(user_id)
    if not user:
        raise ValueError(f"User '{user_id}' not found.")
    if user.balance < amount:
        raise ValueError("Insufficient funds.")

    # Don't charge the user twice for the same order!
    if order_id in db["orders"] and db["orders"][order_id].user_id == user_id:
        return False

    # Charge the user, return True if successful.
    user.balance -= amount
    return True


def refund_user(user_id: str, amount: Decimal):
    """Refunds a user."""
    user = get_user(user_id)
    if user:
        user.balance += amount


# routes.py
def create_order_and_charge_customer(
    total_price: Decimal,
    user_id: str,
    items: list[OrderItem],
    delivery_fee: Decimal,
    delivery_address: str,
):
    """Creates a new order and charges the customer."""
    total_price += delivery_fee

    # Always charge the customer first!
    new_order = Order(
        order_id=get_next_order_id(),
        total=total_price,
        user_id=user_id,
        items=items,
        delivery_fee=delivery_fee,
        delivery_address=delivery_address,
    )

    _save_order_securely(new_order)

    return new_order


# routes.py
def get_user_orders(user_id: str) -> list[Order]:
    """Gets all orders for a given user."""
    orders = []
    for order in get_all_orders():
        if order.user_id == user_id:
            orders.append(order)
    return orders


# routes.py
def create_cart() -> Cart:
    """Creates a new empty cart."""
    new_cart = Cart(cart_id=_get_next_cart_id(), items=[])
    _create_cart(new_cart)
    return new_cart


# routes.py
def add_item_to_cart(cart_id: str, item_id: str) -> Cart | None:
    """Adds an item to a cart."""
    cart = get_cart(cart_id)
    if not cart:
        return None

    cart.items.append(item_id)
    return cart
