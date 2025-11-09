from decimal import Decimal
from typing import List

from .models import MenuItem, Order, OrderItem, User

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
            order_id="1",
            total=Decimal("10.99"),
            user_id="sandy",
            items=[OrderItem(item_id="1", name="Krabby Patty", price=Decimal("5.99"))],
            delivery_fee=Decimal("5.00"),
        ),
        "2": Order(
            order_id="3",
            total=Decimal("26.49"),
            user_id="spongebob",
            items=[
                OrderItem(item_id="6", name="Krusty Krab Complect", price=Decimal("20.50")),
                OrderItem(item_id="1", name="Krabby Patty", price=Decimal("5.99")),
            ],
            delivery_fee=Decimal("0.00"),
        ),
    },
    "next_order_id": 3,
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


def _create_order(order: Order):
    db["orders"][order.order_id] = order


def _get_next_order_id() -> str:
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


# ============================================================
# BUSINESS LOGIC
# High-level business logic for the application.
# ============================================================
def _charge_user(user_id: str, amount: Decimal):
    user = get_user(user_id)
    if not user:
        raise ValueError(f"User '{user_id}' not found.")
    if user.balance < amount:
        raise ValueError("Insufficient funds.")
    user.balance -= amount


# routes.py
def create_order_and_charge_customer(
    total_price: Decimal, user_id: str, items: List[OrderItem], delivery_fee: Decimal
):
    """Creates a new order and charges the customer."""
    total_price += delivery_fee
    # Always charge the customer first!
    _charge_user(user_id, total_price)

    new_order = Order(
        order_id=_get_next_order_id(),
        total=total_price,
        user_id=user_id,
        items=items,
        delivery_fee=delivery_fee,
    )

    # TODO: What if the order creation fails? Add a rollback mechanism before we go to production!
    _create_order(new_order)

    return new_order


# routes.py
def get_user_orders(user_id: str) -> List[Order]:
    """Gets all orders for a given user."""
    orders = []
    for order in get_all_orders():
        if order.user_id == user_id:
            orders.append(order)
    return orders
