"""
Bootstrap Data (Fixtures)

This module contains the initial data to populate the database.
Converted from the original storage.py in-memory database.
"""

from decimal import Decimal

from .models import (
    Cart,
    CartItem,
    MenuItem,
    Order,
    OrderItem,
    PlatformConfig,
    Refund,
    RefundStatus,
    Restaurant,
    User,
)


def get_restaurants():
    """Get initial restaurant data."""
    return [
        Restaurant(
            name="Krusty Krab",
            description="Home of the Krabby Patty!",
            owner="Eugene H. Krabs",
            api_key="key-mrkrabs-1bd647c2-dc5b-4c2b-a316-5ff83786c219",
        ),
        # Adding a second restaurant for multi-tenancy demonstration
        Restaurant(
            name="Chum Bucket",
            description="Plankton's rival restaurant",
            owner="Sheldon J. Plankton",
            api_key="key-plankton-a1b2c3d4-e5f6-4a5b-8c9d-0e1f2a3b4c5d",
        ),
    ]


def get_users():
    """Get initial user data."""
    return [
        User(
            email="sandy@bikinibottom.sea",
            name="Sandy Cheeks",
            balance=Decimal("50.00"),
            password="testpassword",
        ),
        User(
            email="spongebob@bikinibottom.sea",
            name="SpongeBob SquarePants",
            balance=Decimal("20.00"),
            password="i_l0ve_burg3rs",
        ),
        User(
            email="plankton@chum-bucket.sea",
            name="Sheldon Plankton",
            balance=Decimal("100.00"),
            password="i_love_my_wife",
        ),
    ]


def get_menu_items(restaurant_id: int):
    """Get initial menu items for the provided restaurant."""
    return [
        MenuItem(
            restaurant_id=restaurant_id,
            name="Krabby Patty",
            price=Decimal("5.99"),
            available=True,
        ),
        MenuItem(
            restaurant_id=restaurant_id,
            name="Krusty Krab Pizza",
            price=Decimal("12.50"),
            available=True,
        ),
        MenuItem(
            restaurant_id=restaurant_id,
            name="Side of Fries",
            price=Decimal("1.00"),
            available=True,
        ),
        MenuItem(
            restaurant_id=restaurant_id,
            name="Kelp Shake",
            price=Decimal("2.50"),
            available=True,
        ),
        MenuItem(
            restaurant_id=restaurant_id,
            name="Soda",
            price=Decimal("2.75"),
            available=False,
        ),
        MenuItem(
            restaurant_id=restaurant_id,
            name="Krusty Krab Complect",
            price=Decimal("20.50"),
            available=True,
        ),
    ]


def get_orders(restaurant_id: int, user_id: int):
    """Get initial order data."""
    return [
        Order(
            restaurant_id=restaurant_id,
            user_id=user_id,
            total=Decimal("26.49"),
            delivery_fee=Decimal("0.00"),
            delivery_address="122 Conch Street",
            tip=Decimal("0.00"),
        ),
    ]


def get_order_items(order_id: int, items: list[MenuItem]):
    """Get initial order items data."""
    return [
        OrderItem(
            order_id=order_id,
            item_id=item.id,
            name=item.name,
            price=item.price,
        )
        for item in items
    ]


def get_carts(restaurant_id: int):
    """Get initial cart data."""
    return [
        Cart(restaurant_id=restaurant_id),
    ]


def get_cart_items(cart_id: int, items: list[MenuItem]):
    """Get initial cart items data."""
    return [CartItem(cart_id=cart_id, item_id=item.id) for item in items]


def get_refunds(order_id: int):
    """Get initial refund data."""
    return [
        Refund(
            order_id=order_id,
            amount=Decimal("5.30"),
            reason="Late delivery",
            status=RefundStatus.pending,
            auto_approved=False,
            paid=False,
        ),
    ]


def get_platform_config():
    """Get initial platform configuration."""
    return [
        PlatformConfig(
            key="platform_api_key", value="key-sandy-42841a8d-0e65-41db-8cce-8588c23e53dc"
        ),
        PlatformConfig(key="signup_bonus_remaining", value="100.00"),
    ]
