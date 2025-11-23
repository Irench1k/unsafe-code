from copy import deepcopy
from decimal import Decimal

from .models import MenuItem, Order, OrderItem, User

# ============================================================
# DATA STORAGE (In-memory database)
# For an MVP, a simple dictionary will do.
# ============================================================
# v102: Delivery service with fee calculation based on order total
db = {
    "menu_items": {
        "1": MenuItem(id="1", name="Krabby Patty Combo", price=Decimal("12.99"), available=True),
        "2": MenuItem(id="2", name="Coral Bits Meal", price=Decimal("8.99"), available=True),
        "3": MenuItem(id="3", name="Triple Krabby Supreme", price=Decimal("18.99"), available=True),
        "4": MenuItem(id="4", name="Krabby Patty", price=Decimal("3.99"), available=True),
        "5": MenuItem(id="5", name="Fries", price=Decimal("2.49"), available=True),
        "6": MenuItem(id="6", name="Kelp Shake", price=Decimal("3.49"), available=True),
        "7": MenuItem(id="7", name="Coral Bits", price=Decimal("4.49"), available=True),
        "8": MenuItem(id="8", name="Ultimate Krabby Feast", price=Decimal("27.99"), available=True),
    },
    "users": {
        "sandy": User(
            user_id="sandy",
            email="sandy@bikinibottom.sea",
            name="Sandy Cheeks",
            balance=Decimal("999.99"),
            password="testpassword",
        ),
        "patrick": User(
            user_id="patrick",
            email="patrick@bikinibottom.sea",
            name="Patrick Star",
            balance=Decimal("88.52"),
            password="im_with_stupid",
        ),
        "plankton": User(
            user_id="plankton",
            email="plankton@chum-bucket.sea",
            name="Sheldon Plankton",
            balance=Decimal("50.00"),
            password="i_love_my_wife",
        ),
        "spongebob": User(
            user_id="spongebob",
            email="spongebob@krusty-krab.sea",
            name="SpongeBob SquarePants",
            balance=Decimal("22.01"),
            password="i_l0ve_burg3rs",
        ),
    },
    "orders": {
        "1": Order(
            order_id="1",
            total=Decimal("11.48"),
            user_id="patrick",
            items=[
                OrderItem(item_id="4", name="Krabby Patty", price=Decimal("3.99")),
                OrderItem(item_id="5", name="Fries", price=Decimal("2.49")),
            ],
            delivery_fee=Decimal("5.00"),
        ),
        "2": Order(
            order_id="2",
            total=Decimal("27.99"),
            user_id="spongebob",
            items=[OrderItem(item_id="8", name="Ultimate Krabby Feast", price=Decimal("27.99"))],
            delivery_fee=Decimal("0.00"),
        ),
    },
    "next_order_id": 3,
    "api_key": "key-krusty-krub-z1hu0u8o94",
}
SEED_DB = deepcopy(db)


def reset_db():
    db.clear()
    db.update(deepcopy(SEED_DB))


def set_balance(user_id: str, amount: Decimal) -> bool:
    user = get_user(user_id)
    if not user:
        return False
    user.balance = Decimal(str(amount))
    return True


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
def get_all_orders() -> list[Order]:
    """Gets all orders."""
    return list(db["orders"].values())


# routes.py
def get_all_menu_items() -> list[MenuItem]:
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
    total_price: Decimal, user_id: str, items: list[OrderItem], delivery_fee: Decimal
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
def get_user_orders(user_id: str) -> list[Order]:
    """Gets all orders for a given user."""
    orders = []
    for order in get_all_orders():
        if order.user_id == user_id:
            orders.append(order)
    return orders
