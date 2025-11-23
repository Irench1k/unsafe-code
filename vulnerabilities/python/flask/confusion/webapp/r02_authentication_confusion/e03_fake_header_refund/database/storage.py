from copy import deepcopy
from decimal import Decimal

from .models import Cart, MenuItem, Order, OrderItem, Refund, User

# ============================================================
# DATA STORAGE (In-memory database)
# For an MVP, a simple dictionary will do.
# ============================================================
# v203: Refund approval workflow
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
        "sandy@bikinibottom.sea": User(
            user_id="sandy@bikinibottom.sea",
            name="Sandy Cheeks",
            balance=Decimal("999.99"),
            password="testpassword",
        ),
        "patrick@bikinibottom.sea": User(
            user_id="patrick@bikinibottom.sea",
            name="Patrick Star",
            balance=Decimal("85.52"),
            password="im_with_stupid",
        ),
        "plankton@chum-bucket.sea": User(
            user_id="plankton@chum-bucket.sea",
            name="Sheldon Plankton",
            balance=Decimal("50.00"),
            password="i_love_my_wife",
        ),
        "spongebob@krusty-krab.sea": User(
            user_id="spongebob@krusty-krab.sea",
            name="SpongeBob SquarePants",
            balance=Decimal("23.60"),
            password="i_l0ve_burg3rs",
        ),
    },
    "orders": {
        "1": Order(
            order_id="1",
            total=Decimal("14.48"),
            user_id="patrick@bikinibottom.sea",
            items=[
                OrderItem(item_id="4", name="Krabby Patty", price=Decimal("3.99")),
                OrderItem(item_id="5", name="Fries", price=Decimal("2.49")),
            ],
            delivery_fee=Decimal("5.00"),
            delivery_address="120 Conch Street",
            tip=Decimal("3.00"),
        ),
        "2": Order(
            order_id="2",
            total=Decimal("33.00"),
            user_id="spongebob@krusty-krab.sea",
            items=[OrderItem(item_id="8", name="Ultimate Krabby Feast", price=Decimal("27.99"))],
            delivery_fee=Decimal("0.00"),
            delivery_address="122 Conch Street",
            tip=Decimal("5.01"),
        ),
    },
    "carts": {
        "1": Cart(cart_id="1", items=["4", "5"]),
        "2": Cart(cart_id="2", items=["8"]),
    },
    "refunds": {
        "1": Refund(
            refund_id="1",
            order_id="2",
            amount=Decimal("6.60"),
            reason="Late delivery - auto-approved",
            status="approved",
            auto_approved=True,
        ),
    },
    "platform_api_key": "key-sandy-42841a8d-0e65-41db-8cce-8588c23e53dc",
    "restaurant_api_key": "key-krusty-krub-z1hu0u8o94",
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
