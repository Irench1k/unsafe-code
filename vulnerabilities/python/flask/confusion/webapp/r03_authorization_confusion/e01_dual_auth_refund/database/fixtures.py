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
            id="krusty_krab",
            name="Krusty Krab",
            description="Home of the Krabby Patty!",
            owner="Eugene H. Krabs",
            api_key="key-mrkrabs-1bd647c2-dc5b-4c2b-a316-5ff83786c219",
        ),
        # Adding a second restaurant for multi-tenancy demonstration
        Restaurant(
            id="chum_bucket",
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
            user_id="sandy@bikinibottom.sea",
            name="Sandy Cheeks",
            balance=Decimal("50.00"),
            password="testpassword",
        ),
        User(
            user_id="spongebob@bikinibottom.sea",
            name="SpongeBob SquarePants",
            balance=Decimal("20.00"),
            password="i_l0ve_burg3rs",
        ),
        User(
            user_id="plankton@chum-bucket.sea",
            name="Sheldon Plankton",
            balance=Decimal("100.00"),
            password="i_love_my_wife",
        ),
    ]


def get_menu_items():
    """Get initial menu items (for Krusty Krab)."""
    restaurant_id = "krusty_krab"
    return [
        MenuItem(
            id="1",
            restaurant_id=restaurant_id,
            name="Krabby Patty",
            price=Decimal("5.99"),
            available=True,
        ),
        MenuItem(
            id="2",
            restaurant_id=restaurant_id,
            name="Krusty Krab Pizza",
            price=Decimal("12.50"),
            available=True,
        ),
        MenuItem(
            id="3",
            restaurant_id=restaurant_id,
            name="Side of Fries",
            price=Decimal("1.00"),
            available=True,
        ),
        MenuItem(
            id="4",
            restaurant_id=restaurant_id,
            name="Kelp Shake",
            price=Decimal("2.50"),
            available=True,
        ),
        MenuItem(
            id="5",
            restaurant_id=restaurant_id,
            name="Soda",
            price=Decimal("2.75"),
            available=False,
        ),
        MenuItem(
            id="6",
            restaurant_id=restaurant_id,
            name="Krusty Krab Complect",
            price=Decimal("20.50"),
            available=True,
        ),
    ]


def get_orders():
    """Get initial order data."""
    return [
        Order(
            order_id="1",
            restaurant_id="krusty_krab",
            user_id="spongebob@bikinibottom.sea",
            total=Decimal("26.49"),
            delivery_fee=Decimal("0.00"),
            delivery_address="122 Conch Street",
            tip=Decimal("0.00"),
        ),
    ]


def get_order_items():
    """Get initial order items data."""
    return [
        OrderItem(
            order_id="1",
            item_id="6",
            name="Krusty Krab Complect",
            price=Decimal("20.50"),
        ),
        OrderItem(
            order_id="1",
            item_id="1",
            name="Krabby Patty",
            price=Decimal("5.99"),
        ),
    ]


def get_carts():
    """Get initial cart data."""
    return [
        Cart(cart_id="1", restaurant_id="krusty_krab"),
    ]


def get_cart_items():
    """Get initial cart items data."""
    return [
        CartItem(cart_id="1", item_id="1"),
        CartItem(cart_id="1", item_id="3"),
    ]


def get_refunds():
    """Get initial refund data."""
    return [
        Refund(
            refund_id="1",
            order_id="1",
            amount=Decimal("5.298"),
            reason="Late delivery",
            status=RefundStatus.pending,
            auto_approved=False,
            paid=False,
        ),
    ]


def get_platform_config():
    """Get initial platform configuration."""
    return [
        PlatformConfig(key="platform_api_key", value="key-sandy-42841a8d-0e65-41db-8cce-8588c23e53dc"),
        PlatformConfig(key="signup_bonus_remaining", value="100.00"),
    ]
