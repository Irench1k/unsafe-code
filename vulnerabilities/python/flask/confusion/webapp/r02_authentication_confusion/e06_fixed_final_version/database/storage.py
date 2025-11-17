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
            refunded=False,
            items=[
                OrderItem(item_id="6", name="Krusty Krab Complect", price=Decimal("20.50")),
                OrderItem(item_id="1", name="Krabby Patty", price=Decimal("5.99")),
            ],
            delivery_fee=Decimal("0.00"),
            delivery_address="122 Conch Street",
        ),
    },
    "carts": {
        "1": Cart(
            cart_id="1",
            user_id="spongebob@bikinibottom.sea",
            items=["1", "3"],
            active=True,
        ),
    },
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
    "restaurant_api_key": "key-mrkrabs-1bd647c2-dc5b-4c2b-a316-5ff83786c219",
    "platform_api_key": "key-sandy-42841a8d-0e65-41db-8cce-8588c23e53dc",
    "signup_bonus_remaining": Decimal("100.00"),
}
