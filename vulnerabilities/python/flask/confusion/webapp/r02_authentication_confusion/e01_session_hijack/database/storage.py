from copy import deepcopy
from decimal import Decimal

from .models import Cart, MenuItem, Order, OrderItem, Refund, User

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
        "sandy@bikinibottom.sea": User(
            user_id="sandy@bikinibottom.sea",
            name="Sandy Cheeks",
            balance=Decimal("50.00"),
            password="testpassword",
        ),
        "spongebob@bikinibottom.sea": User(
            user_id="spongebob@bikinibottom.sea",
            name="SpongeBob SquarePants",
            balance=Decimal("20.00"),
            password="i_l0ve_burg3rs",
        ),
        "plankton@chum-bucket.sea": User(
            user_id="plankton@chum-bucket.sea",
            name="Sheldon Plankton",
            balance=Decimal("100.00"),
            password="i_love_my_wife",
        ),
    },
    "orders": {
        "1": Order(
            order_id="1",
            total=Decimal("26.49"),
            user_id="spongebob@bikinibottom.sea",
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
    "refunds": {
        "1": Refund(
            refund_id="1",
            order_id="1",
            amount=Decimal("5.298"),
            reason="Late delivery",
            status="pending",
            auto_approved=False,
        ),
    },
    "next_refund_id": 2,
    "signup_bonus_remaining": Decimal("100.00"),
}
SEED_DB = deepcopy(db)


def reset_db():
    db.clear()
    db.update(deepcopy(SEED_DB))


def set_balance(user_id: str, amount: Decimal) -> bool:
    user = db["users"].get(user_id)
    if not user:
        return False
    user.balance = Decimal(str(amount))
    return True
