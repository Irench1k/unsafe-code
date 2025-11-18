"""
Database Fixtures - Complete Database Initialization

This module handles ALL database initialization in a clean, linear, and readable way.
It uses a layered approach:
- Direct inserts for configuration (no business logic needed)
- Business-logic-style functions for complex entities (orders, carts, refunds)
- Natural ordering where child entities are created after parents

This makes it easy to:
- Add new test data
- Modify existing scenarios
- Understand the data flow
- Avoid pre-calculation errors
"""

import logging
from decimal import Decimal

from sqlalchemy.orm import Session

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

logger = logging.getLogger(__name__)


def initialize_all_fixtures(session: Session) -> None:
    """
    Initialize all database fixtures in the correct order.

    This is the main entry point for database initialization.
    Everything is done in a single transaction for consistency.
    """
    try:
        logger.info("Starting database fixture initialization...")

        # 1. Platform Configuration (must exist first for API keys)
        logger.debug("Creating platform configuration...")
        _create_platform_config(session)

        # 2. Restaurants (independent entities)
        logger.debug("Creating restaurants...")
        krusty_krab, chum_bucket = _create_restaurants(session)

        # 3. Menu Items (depend on restaurants)
        logger.debug("Creating menu items...")
        krusty_menu, chum_menu = _create_menu_items(session, krusty_krab, chum_bucket)

        # 4. Users/Customers (independent entities)
        logger.debug("Creating users...")
        users = _create_users(session)

        # 5. Orders with Order Items (complex entities - created together!)
        logger.debug("Creating orders and order items...")
        orders = _create_orders_with_items(
            session, krusty_krab, chum_bucket, krusty_menu, chum_menu, users
        )

        # 6. Carts with Cart Items (created together!)
        logger.debug("Creating carts...")
        _create_carts_with_items(session, krusty_krab, krusty_menu, users)

        # 7. Refunds (depend on orders)
        logger.debug("Creating refunds...")
        _create_refunds(session, orders, users)

        # Commit everything
        session.commit()
        logger.info("Database fixtures initialized successfully!")

    except Exception as e:
        logger.error(f"Error initializing fixtures: {e}")
        session.rollback()
        raise


# ============================================================
# 1. PLATFORM CONFIGURATION
# ============================================================


def _create_platform_config(session: Session) -> dict[str, PlatformConfig]:
    """Create platform-wide configuration."""
    configs = {
        "platform_api_key": PlatformConfig(
            key="platform_api_key", value="key-sandy-42841a8d-0e65-41db-8cce-8588c23e53dc"
        ),
        "signup_bonus_remaining": PlatformConfig(key="signup_bonus_remaining", value="100.00"),
    }

    for config in configs.values():
        session.add(config)
    session.flush()  # Get IDs

    return configs


# ============================================================
# 2. RESTAURANTS
# ============================================================


def _create_restaurants(session: Session) -> tuple[Restaurant, Restaurant]:
    """Create restaurants in Bikini Bottom."""
    krusty_krab = Restaurant(
        name="Krusty Krab",
        description="Home of the Krabby Patty!",
        owner="mr.krabs@krusty-krab.sea",
        api_key="key-mrkrabs-1bd647c2-dc5b-4c2b-a316-5ff83786c219",
    )

    chum_bucket = Restaurant(
        name="Chum Bucket",
        description="Plankton's rival restaurant",
        owner="plankton@chum-bucket.sea",
        api_key="key-plankton-a1b2c3d4-e5f6-4a5b-8c9d-0e1f2a3b4c5d",
    )

    session.add_all([krusty_krab, chum_bucket])
    session.flush()  # Get IDs assigned

    return krusty_krab, chum_bucket


# ============================================================
# 3. MENU ITEMS
# ============================================================


def _create_menu_items(
    session: Session, krusty_krab: Restaurant, chum_bucket: Restaurant
) -> tuple[dict[str, MenuItem], dict[str, MenuItem]]:
    """
    Create menu items for each restaurant.

    Returns dictionaries mapping item names to MenuItem objects for easy reference.
    """
    # Krusty Krab Menu
    krusty_menu = {
        "Krabby Patty": MenuItem(
            restaurant_id=krusty_krab.id,
            name="Krabby Patty",
            price=Decimal("5.99"),
            available=True,
        ),
        "Side of Fries": MenuItem(
            restaurant_id=krusty_krab.id,
            name="Side of Fries",
            price=Decimal("1.00"),
            available=True,
        ),
        "Kelp Shake": MenuItem(
            restaurant_id=krusty_krab.id,
            name="Kelp Shake",
            price=Decimal("2.50"),
            available=True,
        ),
        "Krusty Krab Complect": MenuItem(
            restaurant_id=krusty_krab.id,
            name="Krusty Krab Complect",
            price=Decimal("20.50"),
            available=True,
        ),
        "Ultimate Krusty Krab": MenuItem(
            restaurant_id=krusty_krab.id,
            name="Ultimate Krusty Krab",
            price=Decimal("50.00"),
            available=True,
        ),
    }

    # Chum Bucket Menu
    chum_menu = {
        "Chum Burger": MenuItem(
            restaurant_id=chum_bucket.id,
            name="Chum Burger",
            price=Decimal("10.00"),
            available=True,
        ),
        "ChumBalaya": MenuItem(
            restaurant_id=chum_bucket.id,
            name="ChumBalaya",
            price=Decimal("25.00"),
            available=True,
        ),
    }

    # Add all menu items
    session.add_all(list(krusty_menu.values()) + list(chum_menu.values()))
    session.flush()  # Get IDs assigned

    return krusty_menu, chum_menu


# ============================================================
# 4. USERS
# ============================================================


def _create_users(session: Session) -> dict[str, User]:
    """
    Create all users in the system.

    Returns a dictionary mapping email to User objects for easy reference.
    """
    users_data = [
        {
            "email": "sandy@bikinibottom.sea",
            "name": "Sandy Cheeks",
            "balance": Decimal("50.00"),
            "password": "testpassword",
        },
        {
            "email": "mr.krabs@krusty-krab.sea",
            "name": "Eugene H. Krabs",
            "balance": Decimal("1000.00"),
            "password": "mon3y_m0ney_m0ney_m0ney",
        },
        {
            "email": "spongebob@bikinibottom.sea",
            "name": "SpongeBob SquarePants",
            "balance": Decimal("20.00"),
            "password": "i_l0ve_burg3rs",
        },
        {
            "email": "plankton@chum-bucket.sea",
            "name": "Sheldon Plankton",
            "balance": Decimal("100.00"),
            "password": "i_love_my_wife",
        },
        {
            "email": "karen@chum-bucket.sea",
            "name": "Karen the Computer",
            "balance": Decimal("150.00"),
            "password": "10100101",
        },
        {
            "email": "squidward@krusty-krab.sea",
            "name": "Squidward Tentacles",
            "balance": Decimal("100.00"),
            "password": "i_hate_my_job",
        },
        {
            "email": "patrick@krusty-krab.sea",
            "name": "Patrick Star",
            "balance": Decimal("10.00"),
            "password": "1234567890",
        },
    ]

    users = {}
    for data in users_data:
        user = User(**data)
        session.add(user)
        users[data["email"]] = user

    session.flush()  # Get IDs assigned

    return users


# ============================================================
# 5. ORDERS WITH ORDER ITEMS
# ============================================================


def _create_orders_with_items(
    session: Session,
    krusty_krab: Restaurant,
    chum_bucket: Restaurant,
    krusty_menu: dict[str, MenuItem],
    chum_menu: dict[str, MenuItem],
    users: dict[str, User],
) -> dict[str, Order]:
    """
    Create orders with their order items.

    This is the beautiful part - we create items first, then calculate totals!
    No more pre-calculation needed. No more fragile manual math.
    """
    orders = {}

    # SpongeBob's order at Krusty Krab
    spongebob_order = _create_order_with_items(
        session=session,
        customer=users["spongebob@bikinibottom.sea"],
        restaurant=krusty_krab,
        items=[
            krusty_menu["Krusty Krab Complect"],  # $20.50
            krusty_menu["Krabby Patty"],  # $5.99
        ],
        delivery_address="122 Conch Street",
        delivery_fee=Decimal("0.00"),
        tip=Decimal("5.00"),
    )
    orders["spongebob_krusty"] = spongebob_order

    # Plankton's order at Chum Bucket
    plankton_order = _create_order_with_items(
        session=session,
        customer=users["plankton@chum-bucket.sea"],
        restaurant=chum_bucket,
        items=[
            chum_menu["Chum Burger"],  # $10.00
        ],
        delivery_address="Chum Bucket Street",
        delivery_fee=Decimal("5.00"),
        tip=Decimal("3.00"),
    )
    orders["plankton_chum"] = plankton_order

    return orders


def _create_order_with_items(
    session: Session,
    customer: User,
    restaurant: Restaurant,
    items: list[MenuItem],
    delivery_address: str,
    delivery_fee: Decimal,
    tip: Decimal = Decimal("0.00"),
) -> Order:
    """
    Create an order with its items in one go.

    This helper function:
    1. Calculates the subtotal from items (no manual math!)
    2. Calculates the total (subtotal + delivery + tip)
    3. Creates the order
    4. Creates order items (snapshots of menu items)
    5. Returns the complete order

    This is how orders SHOULD be created - naturally and safely!
    """
    # Calculate subtotal from actual items
    subtotal = sum(item.price for item in items)
    total = subtotal + delivery_fee + tip

    # Create the order
    order = Order(
        restaurant_id=restaurant.id,
        user_id=customer.id,
        total=total,
        delivery_fee=delivery_fee,
        delivery_address=delivery_address,
        tip=tip,
    )
    session.add(order)
    session.flush()  # Get order ID

    # Create order items (snapshots of menu items at time of order)
    order_items = []
    for menu_item in items:
        order_item = OrderItem(
            order_id=order.id,
            item_id=menu_item.id,
            name=menu_item.name,
            price=menu_item.price,
        )
        order_items.append(order_item)
        session.add(order_item)

    session.flush()

    logger.debug(
        f"Created order {order.id} for {customer.email}: "
        f"{len(items)} items, subtotal=${subtotal}, total=${total}"
    )

    return order


# ============================================================
# 6. CARTS WITH CART ITEMS
# ============================================================


def _create_carts_with_items(
    session: Session,
    krusty_krab: Restaurant,
    krusty_menu: dict[str, MenuItem],
    users: dict[str, User],
) -> list[Cart]:
    """
    Create shopping carts with items.

    For demonstration purposes, we create a cart with some items.
    """
    carts = []

    # Create a cart for Krusty Krab
    cart = _create_cart_with_items(
        session=session,
        restaurant=krusty_krab,
        items=[
            krusty_menu["Krabby Patty"],
            krusty_menu["Side of Fries"],
        ],
        user=users["spongebob@bikinibottom.sea"],
    )
    carts.append(cart)

    return carts


def _create_cart_with_items(
    session: Session,
    restaurant: Restaurant,
    items: list[MenuItem],
    user: User,
) -> Cart:
    """
    Create a cart with items.

    This creates the cart and adds items to it atomically.
    """
    # Create the cart
    cart = Cart(restaurant_id=restaurant.id, user_id=user.id)
    session.add(cart)
    session.flush()  # Get cart ID

    # Add items to cart
    for menu_item in items:
        cart_item = CartItem(
            cart_id=cart.id,
            item_id=menu_item.id,
        )
        session.add(cart_item)

    session.flush()

    logger.debug(f"Created cart {cart.id} with {len(items)} items")

    return cart


# ============================================================
# 7. REFUNDS
# ============================================================


def _create_refunds(
    session: Session,
    orders: dict[str, Order],
    users: dict[str, User],
) -> list[Refund]:
    """
    Create refund requests for orders.

    This demonstrates the refund workflow in the training scenario.
    """
    refunds = []

    # Create a pending refund for SpongeBob's order
    spongebob_order = orders["spongebob_krusty"]
    refund = Refund(
        order_id=spongebob_order.id,
        amount=Decimal("5.30"),
        reason="Late delivery",
        status=RefundStatus.pending,
        auto_approved=False,
        paid=False,
    )
    session.add(refund)
    refunds.append(refund)

    session.flush()

    logger.debug(f"Created {len(refunds)} refund(s)")

    return refunds


# ============================================================
# UTILITY FUNCTIONS (if needed for debugging/inspection)
# ============================================================


def print_fixture_summary(session: Session) -> None:
    """
    Print a summary of all fixtures created (useful for debugging).

    Call this after initialize_all_fixtures() if you want to see what was created.
    """
    from sqlalchemy import func, select

    tables = [
        ("Restaurants", Restaurant),
        ("Menu Items", MenuItem),
        ("Users", User),
        ("Orders", Order),
        ("Order Items", OrderItem),
        ("Carts", Cart),
        ("Cart Items", CartItem),
        ("Refunds", Refund),
        ("Platform Config", PlatformConfig),
    ]

    print("\n" + "=" * 60)
    print("DATABASE FIXTURE SUMMARY")
    print("=" * 60)

    for name, model in tables:
        count = session.execute(select(func.count()).select_from(model)).scalar()
        print(f"{name:.<30} {count:>3} records")

    print("=" * 60 + "\n")
