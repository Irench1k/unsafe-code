"""
Business Logic Layer

Contains high-level business operations that coordinate multiple repository calls
and enforce business rules. No direct database access - all operations go through
the repository.
"""

import logging
from decimal import Decimal
from typing import Literal

from flask import g, session

from ..config import OrderConfig
from ..errors import CheekyApiError
from .models import (
    Cart,
    Coupon,
    CouponType,
    MenuItem,
    Order,
    Refund,
    RefundStatus,
    Restaurant,
    User,
)
from .repository import (
    add_cart_item,
    find_order_by_id,
    find_order_items,
    find_orders_by_user,
    find_user_by_email,
    find_user_by_id,
    get_cart_items,
    get_refund_by_order_id,
    get_signup_bonus_remaining,
    save_cart,
    save_cart_item,
    save_menu_item,
    save_refund,
    save_restaurant,
    save_user,
    set_signup_bonus_remaining,
)

logger = logging.getLogger(__name__)


# ============================================================
# RESTAURANT SERVICES
# ============================================================
def serialize_restaurant(restaurant: Restaurant) -> dict:
    """Serializes a restaurant to a JSON-compatible dict."""
    return {
        "id": restaurant.id,
        "name": restaurant.name,
        "description": restaurant.description,
        "domain": restaurant.domain,
    }


def serialize_restaurant_creation(restaurant: Restaurant) -> dict:
    """Serializes a restaurant creation to a JSON-compatible dict."""
    return {
        "id": restaurant.id,
        "name": restaurant.name,
        "description": restaurant.description,
        "owner": restaurant.owner,
        "api_key": restaurant.api_key,
        "domain": restaurant.domain,
        "status": "created",
    }


def serialize_restaurants(restaurants: list[Restaurant]) -> list[dict]:
    """Serializes a list of restaurants."""
    return [serialize_restaurant(restaurant) for restaurant in restaurants]


def serialize_restaurant_users(users: list[User]) -> list[dict]:
    """Serializes a list of restaurant users to JSON-compatible dicts."""
    return [{"email": user.email, "name": user.name} for user in users]


# ============================================================
# MENU SERVICES
# ============================================================
def serialize_menu_item(menu_item: MenuItem) -> dict:
    """Serializes a single menu item."""
    return {
        "id": menu_item.id,
        "restaurant_id": menu_item.restaurant_id,
        "name": menu_item.name,
        "price": str(menu_item.price),
        "available": menu_item.available,
    }


def serialize_menu_items(menu_items: list) -> list[dict]:
    """Serializes a list of menu items to JSON-compatible dicts."""
    return [serialize_menu_item(item) for item in menu_items]


def apply_menu_item_changes(menu_item: MenuItem, fields: dict) -> MenuItem:
    """Apply validated field updates and persist the menu item."""
    allowed = {"name", "price", "available"}
    for field in allowed:
        if field in fields:
            setattr(menu_item, field, fields[field])
    save_menu_item(menu_item)
    return menu_item


def create_menu_item_for_restaurant(restaurant_id: int, fields: dict) -> MenuItem:
    """Create and persist a menu item for a restaurant."""
    allowed = {"name", "price", "available"}
    payload = {key: fields[key] for key in allowed if key in fields}
    payload.setdefault("available", True)
    menu_item = MenuItem(restaurant_id=restaurant_id, **payload)
    save_menu_item(menu_item)
    return menu_item


# ============================================================
# COUPON SERVICES
# ============================================================
def serialize_coupon(coupon: Coupon) -> dict:
    """Serializes a coupon to a JSON-compatible dict."""
    return {
        "id": coupon.id,
        "restaurant_id": coupon.restaurant_id,
        "code": coupon.code,
        "value": str(coupon.value),
    }


def serialize_coupons(coupons: list[Coupon]) -> list[dict]:
    """Serializes a list of coupons to JSON-compatible dicts."""
    return [serialize_coupon(coupon) for coupon in coupons]


# ============================================================
# USER SERVICES
# ============================================================
def create_user(email: str, password: str, name: str) -> None:
    """Creates a new user."""
    user = User(email=email, name=name, password=password)
    save_user(user)
    logger.info(f"User created: {email}")


def apply_signup_bonus(email: str) -> None:
    """Applies a signup bonus to a newly registered user."""
    user = find_user_by_email(email)
    if not user:
        logger.warning(f"Cannot apply signup bonus - user not found: {email}")
        return

    remaining = get_signup_bonus_remaining()

    if remaining < OrderConfig.SIGNUP_BONUS:
        logger.warning(f"Insufficient signup bonus remaining for {email}: {remaining}")
        return

    user.balance += OrderConfig.SIGNUP_BONUS
    save_user(user)
    set_signup_bonus_remaining(remaining - OrderConfig.SIGNUP_BONUS)
    logger.info(f"Signup bonus applied to {email}: {OrderConfig.SIGNUP_BONUS}")


def increment_user_balance(email: str, amount: Decimal) -> Decimal | None:
    """Increments a user's balance and returns the new balance."""
    user = find_user_by_email(email)
    if not user:
        logger.warning(f"Cannot increment balance - user not found: {email}")
        return None

    user.balance += amount
    save_user(user)
    logger.info(f"Balance updated for {email}: +{amount} = {user.balance}")
    return user.balance


def get_current_user(email: str | None = None) -> User | None:
    """Gets the current user from the database."""

    user_email = email or getattr(g, "email", None) or session.get("email")
    if not user_email:
        logger.warning("No email provided and no user in request context")
        return None

    return find_user_by_email(user_email)


# ============================================================
# ORDER SERVICES
# ============================================================
def get_user_orders(user_id: int) -> list[Order]:
    """Gets all orders for a given user."""
    return find_orders_by_user(user_id)


def serialize_order(order: Order) -> dict:
    """Serializes an order to a JSON-compatible dict."""
    # Get order items from database
    order_items = find_order_items(order.id)

    return {
        "order_id": order.id,
        "restaurant_id": order.restaurant_id,
        "user_id": order.user_id,
        "total": str(order.total),
        "delivery_fee": str(order.delivery_fee),
        "delivery_address": order.delivery_address,
        "tip": str(order.tip),
        "discount": str(order.discount),
        "created_at": order.created_at.isoformat(),
        "items": [
            {
                "item_id": item.item_id,
                "name": item.name,
                "price": str(item.price),
            }
            for item in order_items
        ],
        "status": order.status.value,
    }


def serialize_orders(orders: list[Order]) -> list[dict]:
    """Serializes a list of orders to JSON-compatible dicts."""
    return [serialize_order(order) for order in orders]


def find_order_owner(order_id: int | str) -> int | None:
    """Finds the owner of an order."""
    order = find_order_by_id(order_id)
    if not order:
        logger.warning(f"Order not found: {order_id}")
        return None
    return order.user_id


# ============================================================
# CART SERVICES
# ============================================================
def create_cart(restaurant_id: int, user_id: int) -> Cart:
    """Creates and persists a new empty cart."""
    new_cart = Cart(restaurant_id=restaurant_id, user_id=user_id)
    save_cart(new_cart)
    logger.debug(f"Cart created: {new_cart.id} for user {user_id}")
    return new_cart


def add_item_to_cart(
    cart_id: int | str, item_id: int | str, name: str, price: Decimal, quantity: int = 1
) -> None:
    """
    Adds an item to a cart.

    Assume authorization and validation already performed by controller.
    """
    add_cart_item(cart_id, item_id, name, price, quantity)
    logger.debug(f"Item {item_id} added to cart {cart_id}")


def _calculate_coupon_discount(coupon: Coupon, price: Decimal) -> Decimal:
    """Calculates the discount for a coupon."""
    if coupon.type == CouponType.fixed_amount:
        return min(coupon.value, price)
    elif coupon.type == CouponType.discount_percent:
        return (price * coupon.value / 100).quantize(Decimal("1.00"))
    elif coupon.type == CouponType.free_item_sku:
        return price
    elif coupon.type == CouponType.buy_x_get_y_free:
        # This coupon type is handled separately in calculate_cart_price()
        return Decimal("0.00")
    else:
        raise CheekyApiError(f"Invalid coupon type: {coupon.type.value}")


def add_coupon_to_cart(cart: Cart, coupon: Coupon) -> None:
    """Adds a coupon to a cart."""
    for item in get_cart_items(cart.id):
        if item.item_id == coupon.item_id:
            item.coupon_id = coupon.id
            item.price = item.price - _calculate_coupon_discount(coupon, item.price)
            logger.info(f"Coupon {coupon.id} applied to item {item.item_id} in cart {cart.id}")
            save_cart_item(item)
            return

    logger.warning(
        f"Coupon {coupon.id} not applied, because item {coupon.item_id} not found in cart {cart.id}"
    )


# ============================================================
# REFUND SERVICES
# ============================================================
def create_refund(order_id: int, amount: Decimal, reason: str, auto_approved: bool) -> Refund:
    """Creates a new refund with a generated ID."""
    status = RefundStatus.approved if auto_approved else RefundStatus.pending
    refund = Refund(
        order_id=order_id,
        amount=amount,
        reason=reason,
        status=status,
        auto_approved=auto_approved,
    )
    save_refund(refund)
    return refund


def process_refund(refund: Refund, user_id: int) -> None:
    """Processes a refund: saves it and credits user if auto-approved."""
    if refund.status == RefundStatus.approved and not refund.paid:
        refund_user(user_id, refund.amount)
        refund.paid = True
        logger.info(f"Approved refund processed: {refund.id} of {refund.amount} for {user_id}")
    else:
        logger.error(
            f"Refund status: {refund.status}. Refund of {refund.amount} for {user_id} is not paid."
        )
    save_refund(refund)


def serialize_refund(refund: Refund) -> dict:
    """Serializes a refund to a JSON-compatible dict."""
    return {
        "refund_id": refund.id,
        "order_id": refund.order_id,
        "amount": str(refund.amount),
        "reason": refund.reason,
        "status": refund.status.value,  # Enum value
        "auto_approved": refund.auto_approved,
        "paid": refund.paid,
        "created_at": refund.created_at.isoformat(),
    }


def update_order_refund_status(
    order_id: int | str, status: Literal["approved", "rejected"]
) -> Refund | None:
    """Updates the status of a refund in the database."""
    refund = get_refund_by_order_id(order_id)
    if refund:
        # Integrity check: refunds are adjustable ONLY while in `pending` state
        if refund.status != RefundStatus.pending:
            raise CheekyApiError("Refund is not in pending state anymore")

        refund.status = RefundStatus.approved if status == "approved" else RefundStatus.rejected
        refund_owner = find_order_owner(order_id)
        if refund_owner is not None:
            process_refund(refund, refund_owner)
            return refund
        logger.warning(f"Unable to find owner for order {order_id}")
        return None
    logger.warning(f"Refund not found for order {order_id}")
    return None


# ============================================================
# PAYMENT SERVICES
# ============================================================
def charge_user(user_id: int, amount: Decimal) -> bool:
    """Debit a user's balance inside the current transaction."""
    user = find_user_by_id(user_id)
    if not user:
        raise ValueError(f"User '{user_id}' not found.")
    if user.balance < amount:
        raise ValueError("Insufficient funds.")

    # Charge the user
    user.balance -= amount
    save_user(user)
    logger.info(f"User charged: {user_id} - {amount}")
    return True


def refund_user(user_id: int, amount: Decimal) -> None:
    """Refunds a user by adding the amount back to their balance."""
    user = find_user_by_id(user_id)
    if not user:
        logger.error(f"Cannot refund - user not found: {user_id}")
        return

    user.balance += amount
    save_user(user)
    logger.info(f"User refunded: {user_id} + {amount}")


# ============================================================
# RESTAURANT SERVICES
# ============================================================
def create_restaurant(name: str, description: str, domain: str, owner: str) -> Restaurant:
    """Creates a new restaurant with auto-generated API key."""
    import uuid

    api_key = f"key-{domain.replace('.', '-')}-{uuid.uuid4()}"
    restaurant = Restaurant(
        name=name,
        description=description or f"Welcome to {name}!",
        domain=domain,
        owner=owner,
        api_key=api_key,
    )
    save_restaurant(restaurant)
    logger.info(f"Restaurant created: {restaurant.id} - {name}")
    return restaurant


def update_restaurant(
    restaurant: Restaurant,
    name: str | None = None,
    description: str | None = None,
    domain: str | None = None,
) -> Restaurant:
    """Updates a restaurant."""
    restaurant.name = name or restaurant.name
    restaurant.description = description or restaurant.description
    restaurant.domain = domain or restaurant.domain
    save_restaurant(restaurant)
    return restaurant
