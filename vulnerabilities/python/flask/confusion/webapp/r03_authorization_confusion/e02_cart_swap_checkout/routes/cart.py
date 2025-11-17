from decimal import Decimal

from flask import Blueprint, g, jsonify

from ..auth.decorators import require_auth
from ..database.repository import find_cart_by_id, find_menu_item_by_id, get_cart_items
from ..database.services import (
    add_item_to_cart,
    create_cart,
    create_order_from_checkout,
    prepare_cart_for_checkout,
    save_order_securely,
    serialize_cart,
    serialize_order,
)
from ..utils import (
    get_decimal_param,
    get_param,
    get_restaurant_id,
    require_condition,
    require_int_param,
    require_ownership,
)

bp = Blueprint("cart", __name__, url_prefix="/cart")


@bp.post("")
@require_auth(["customer"])
def create_new_cart():
    """
    Creates a new empty cart.

    This is step 1 of the new checkout flow. The cart gets an ID that
    the client will use in subsequent requests to add items.
    """
    restaurant_id = get_restaurant_id()
    new_cart = create_cart(restaurant_id, g.user_id)
    return jsonify(serialize_cart(new_cart)), 201


@bp.post("/<int:cart_id>/items")
@require_auth(["customer"])
def add_item_to_cart_endpoint(cart_id: int):
    """
    Adds a single item to an existing cart.

    This is step 2 of the new checkout flow. Can be called multiple times
    to add different items.
    """
    item_id_int = require_int_param("item_id")

    cart = find_cart_by_id(cart_id)
    require_condition(cart, f"Cart {cart_id} not found")

    # Authorization check: user must be the owner of the cart
    require_ownership(cart.user_id, g.user_id, "cart")

    # Integrity check: cart must be active
    require_condition(cart.active, f"Cart {cart_id} is not active")

    # Fetch and validate menu item
    menu_item = find_menu_item_by_id(item_id_int)
    require_condition(menu_item, f"Menu item {item_id_int} not found")

    # Integrity check: menu item must be available
    require_condition(menu_item.available, f"Menu item {item_id_int} is not available")

    # Integrity check: menu item must belong to same restaurant as cart
    require_condition(
        menu_item.restaurant_id == cart.restaurant_id,
        f"Menu item {item_id_int} does not belong to restaurant {cart.restaurant_id}",
    )

    add_item_to_cart(cart_id, item_id_int)
    return jsonify(serialize_cart(cart)), 200


@bp.post("/<int:cart_id>/checkout")
@require_auth(["customer"])
def checkout_cart(cart_id: int):
    """Checks out a cart and creates an order."""
    # Parse inputs
    tip = abs(get_decimal_param("tip", Decimal("0.00")))
    delivery_address = get_param("delivery_address") or ""

    # Fetch and validate cart
    cart = find_cart_by_id(cart_id)
    require_condition(cart, f"Cart {cart_id} not found")

    # Authorization check: user must be the owner of the cart
    require_ownership(cart.user_id, g.user_id, "cart")

    # Integrity check: cart must be active
    require_condition(cart.active, f"Cart {cart_id} is not active")

    # Get cart items from the database
    cart_items = get_cart_items(cart_id)
    require_condition(cart_items, f"Cart {cart_id} is empty")

    # Validate items and calculate totals
    hydrated_items, subtotal, delivery_fee = prepare_cart_for_checkout(cart_items)
    require_condition(subtotal, f"Cart {cart_id} is empty")

    # Integrity check: user must have sufficient balance
    require_condition(g.balance >= subtotal + delivery_fee + tip, "Insufficient balance")

    # Create and save order
    order, order_items = create_order_from_checkout(
        user_id=g.user_id,
        restaurant_id=cart.restaurant_id,
        total=subtotal + delivery_fee + tip,
        items=hydrated_items,
        delivery_fee=delivery_fee,
        delivery_address=delivery_address,
        tip=tip,
    )

    save_order_securely(order, order_items)
    return jsonify(serialize_order(order)), 201
