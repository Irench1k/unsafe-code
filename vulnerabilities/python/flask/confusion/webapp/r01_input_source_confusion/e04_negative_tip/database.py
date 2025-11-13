from decimal import Decimal
from typing import List

from .models import Cart, MenuItem, Order, OrderItem, User

# ============================================================
# DATA STORAGE (In-memory database)
# For an MVP, a simple dictionary will do.
# ============================================================
db = {
    "menu_items": {
        "1": MenuItem(id="1", name="Krabby Patty", price=Decimal("5.99"), available=True),
        "2": MenuItem(id="2", name="Krusty Krab Pizza", price=Decimal("12.50"), available=True),
        "3": MenuItem(id="3", name="Side of Fries", price=Decimal("1.00"), available=True),
        "4": MenuItem(id="4", name="Kelp Shake", price=Decimal("2.50"), available=True),
        "5": MenuItem(id="5", name="Soda", price=Decimal("2.75"), available=False),
        "6": MenuItem(id="6", name="Krusty Krab Complect", price=Decimal("20.50"), available=True),
    },
    "users": {
        "sandy": User(
            user_id="sandy",
            email="sandy.cheeks@bikinibottom.com",
            name="Sandy Cheeks",
            balance=Decimal("50.00"),
            password="testpassword",
        ),
        "spongebob": User(
            user_id="spongebob",
            email="spongebob.squarepants@bikinibottom.com",
            name="SpongeBob SquarePants",
            balance=Decimal("20.00"),
            password="i_l0ve_burg3rs",
        ),
    },
    "orders": {
        "1": Order(
            order_id="3",
            total=Decimal("26.49"),
            user_id="spongebob",
            items=[
                OrderItem(item_id="6", name="Krusty Krab Complect", price=Decimal("20.50")),
                OrderItem(item_id="1", name="Krabby Patty", price=Decimal("5.99")),
            ],
            delivery_fee=Decimal("0.00"),
            delivery_address="122 Conch Street",
        ),
    },
    "next_order_id": 2,
    "carts": {
        "1": Cart(cart_id="1", items=["1", "3"]),
    },
    "next_cart_id": 2,
    "api_key": "key-krusty-krub-z1hu0u8o94",
}

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


def save_order_securely(order: Order):
    """Charge customer and save order in DB, now with idempotency & rollback!"""
    charged_successfully = False

    try:
        charged_successfully = charge_user(order.user_id, order.total, order.order_id)
        db["orders"][order.order_id] = order
    except Exception as e:
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
def get_all_orders() -> List[Order]:
    """Gets all orders."""
    return list(db["orders"].values())


# routes.py
def get_all_menu_items() -> List[MenuItem]:
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
def get_user_orders(user_id: str) -> List[Order]:
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
