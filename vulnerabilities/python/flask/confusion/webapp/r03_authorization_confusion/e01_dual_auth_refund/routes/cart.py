from decimal import Decimal

from flask import Blueprint, g, jsonify, request

from ..auth.decorators import require_auth
from ..database.repository import find_cart_by_id, find_menu_item_by_id, get_cart_items
from ..database.services import (
    add_item_to_cart,
    create_cart,
    create_order_from_checkout,
    save_order_securely,
    serialize_cart,
    serialize_order,
)
from ..errors import CheekyApiError
from ..utils import (
    check_cart_price_and_delivery_fee,
    get_restaurant_id,
)

bp = Blueprint("cart", __name__, url_prefix="/cart")


def _parse_positive_int(value: str, label: str) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        raise CheekyApiError(f"Invalid {label}") from None
    if parsed <= 0:
        raise CheekyApiError(f"Invalid {label}")
    return parsed


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


@bp.post("/<cart_id>/items")
@require_auth(["customer"])
def add_item_to_cart_endpoint(cart_id):
    """
    Adds a single item to an existing cart.

    This is step 2 of the new checkout flow. Can be called multiple times
    to add different items. Expects JSON body with item_id.

    Note: Flask's request.json automatically parses JSON bodies when
    Content-Type is application/json.
    """
    if not request.is_json or not request.json:
        raise CheekyApiError("JSON body required")

    item_id = request.json.get("item_id")
    cart_id_int = _parse_positive_int(cart_id, "cart_id")
    item_id_int = _parse_positive_int(item_id, "item_id")
    cart = find_cart_by_id(cart_id_int)
    if not cart:
        raise CheekyApiError("Cart not found")

    updated_cart = add_item_to_cart(cart_id_int, item_id_int)
    return jsonify(serialize_cart(updated_cart)), 200


@bp.post("/<cart_id>/checkout")
@require_auth(["customer"])
def checkout_cart(cart_id):
    """Checks out a cart and creates an order."""
    cart_id_int = _parse_positive_int(cart_id, "cart_id")
    cart = find_cart_by_id(cart_id_int)
    if not cart:
        raise CheekyApiError("Cart not found")

    # Authorization check: user must be the owner of the cart
    if cart.user_id != g.user_id:
        raise CheekyApiError(f"User {g.user_id} is not the owner of cart {cart_id}")

    # Integrity check: cart must be active
    if not cart.active:
        raise CheekyApiError(f"Cart {cart_id} is not active")

    # Get cart items from the database
    cart_items = get_cart_items(cart_id_int)
    if not cart_items:
        raise CheekyApiError("Cart is empty")

    # Integrity check: all items must be available
    hydrated_items = []
    for item in cart_items:
        menu_item = find_menu_item_by_id(item.item_id)
        if not menu_item:
            raise CheekyApiError(f"Menu item {item.item_id} not found")
        if not menu_item.available:
            raise CheekyApiError(f"Menu item {item.item_id} is not available")
        hydrated_items.append(
            {
                "item_id": menu_item.id,
                "name": menu_item.name,
                "price": menu_item.price,
            }
        )

    # Get user input - handle both JSON and form data
    user_data = request.json if request.is_json else request.form

    # Some users were "accidentally" giving negative tips, no more!
    tip = abs(Decimal(user_data.get("tip", 0)))

    # Price and delivery fee calculation is the same for both branches
    total_price, delivery_fee = check_cart_price_and_delivery_fee(cart_items)
    if not total_price:
        raise CheekyApiError("Item not available, sorry!")

    if g.balance < total_price + delivery_fee + tip:
        raise CheekyApiError("Insufficient balance")

    delivery_address = user_data.get("delivery_address", "")

    order, order_items = create_order_from_checkout(
        user_id=g.user_id,
        restaurant_id=cart.restaurant_id,
        total=total_price + delivery_fee + tip,
        items=hydrated_items,
        delivery_fee=delivery_fee,
        delivery_address=delivery_address,
        tip=tip,
    )

    save_order_securely(order, order_items)
    return jsonify(serialize_order(order)), 201
