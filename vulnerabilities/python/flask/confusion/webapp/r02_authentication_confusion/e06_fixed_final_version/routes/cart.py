from decimal import Decimal

from flask import Blueprint, g, jsonify, request

from ..auth.decorators import require_auth
from ..database.repository import find_cart_by_id, save_cart
from ..database.services import (
    add_item_to_cart,
    create_cart,
    create_order_from_checkout,
    save_order_securely,
    serialize_cart,
    serialize_order,
)
from ..errors import CheekyApiError
from ..utils import check_cart_price_and_delivery_fee, convert_item_ids_to_order_items

bp = Blueprint("cart", __name__, url_prefix="/cart")


@bp.post("")
@require_auth(["customer"])
def create_new_cart():
    """
    Creates a new empty cart.

    This is step 1 of the new checkout flow. The cart gets an ID that
    the client will use in subsequent requests to add items.
    """
    new_cart = create_cart(g.email)
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
    updated_cart = add_item_to_cart(cart_id, item_id, g.email)
    return jsonify(serialize_cart(updated_cart)), 200


@bp.post("/<cart_id>/checkout")
@require_auth(["customer"])
def checkout_cart(cart_id):
    """Checks out a cart and creates an order."""
    cart = find_cart_by_id(cart_id)
    if not cart or not cart.items:
        raise CheekyApiError("Cart not found")

    if cart.user_id != g.email:
        raise CheekyApiError("Cart does not belong to user")

    if not cart.active:
        raise CheekyApiError("Cart is no longer active")

    # Get user input - handle both JSON and form data
    user_data = request.json if request.is_json else request.form

    # Some users were "accidentally" giving negative tips, no more!
    tip = abs(Decimal(user_data.get("tip", 0)))

    # Price and delivery fee calculation is the same for both branches
    total_price, delivery_fee = check_cart_price_and_delivery_fee(cart.items)
    if not total_price:
        raise CheekyApiError("Item not available, sorry!")

    if g.balance < total_price + delivery_fee + tip:
        raise CheekyApiError("Insufficient balance")

    items = convert_item_ids_to_order_items(cart.items)
    delivery_address = user_data.get("delivery_address", "")

    new_order = create_order_from_checkout(
        user_id=g.email,
        total=total_price + delivery_fee + tip,
        items=[item.model_dump() for item in items],
        delivery_fee=delivery_fee,
        delivery_address=delivery_address,
        tip=tip,
    )

    save_order_securely(new_order)

    # Deactivate cart to prevent reuse after checkout
    cart.active = False
    save_cart(cart)
    return jsonify(serialize_order(new_order)), 201
