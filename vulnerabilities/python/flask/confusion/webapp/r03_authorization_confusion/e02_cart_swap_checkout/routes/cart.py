from decimal import Decimal
from functools import wraps

from flask import Blueprint, g, session

from ..auth.decorators import require_auth
from ..database.repository import find_cart_by_id, find_menu_item_by_id, find_restaurant_by_id, get_cart_items
from ..database.services import (
    add_item_to_cart,
    calculate_cart_price,
    charge_user,
    create_cart,
    create_order_from_checkout,
    save_order_securely,
    serialize_cart,
    serialize_order,
)
from ..utils import (
    created_response,
    get_decimal_param,
    get_param,
    get_restaurant_id,
    require_condition,
    require_int_param,
    require_ownership,
    require_restaurant_id,
    success_response,
)

bp = Blueprint("cart", __name__, url_prefix="/cart")


def resolve_trusted_cart():
    """
    Identify the most trusted cart ID, authorize and validate it.

    We prefer the signed cart ID from the session, but need to fall back to the cart ID
    from the path for legacy mobile app users (app is still using Basic Auth).

    This should apply to all /cart endpoints, apart from POST /cart (where we create a new cart).
    """
    trusted_cart_id = session.get("cart_id") or g.cart_id
    require_condition(trusted_cart_id, "Cart ID is required")

    trusted_cart = find_cart_by_id(trusted_cart_id)
    require_condition(trusted_cart, f"Cart {trusted_cart_id} not found")

    # Authorization check: user must be the owner of the cart
    require_ownership(trusted_cart.user_id, g.user_id, "cart")

    # Integrity check: cart must be active
    require_condition(trusted_cart.active, f"Cart {trusted_cart_id} is not active")

    return trusted_cart


@bp.url_value_preprocessor
def preprocess_cart_id(endpoint, values):
    """Early middleware to replace untrusted cart ID from the path with authorized cart object."""
    if "cart_id" in values:
        g.cart_id = values.pop("cart_id")
        # TODO: I'd like to systemically replace cart ID with authorized cart object, but user_id
        # is only set at decorator level right now, so not in @bp.url_value_preprocessor...
        # values["cart"] = resolve_trusted_cart()


@bp.post("")
@require_auth(["customer"])
def create_new_cart():
    """
    Creates a new empty cart.

    This is step 1 of the new checkout flow. The cart gets an ID that
    the client will use in subsequent requests to add items.
    """
    if "cart_id" in session:
        # Prevent cart spam
        existing_cart = find_cart_by_id(session["cart_id"])
        require_condition(existing_cart, f"Cart {session['cart_id']} not found")
        require_ownership(existing_cart.user_id, g.user_id, "cart")
        return success_response(serialize_cart(existing_cart))

    restaurant_id = require_restaurant_id()
    restaurant = find_restaurant_by_id(restaurant_id)
    require_condition(restaurant, f"Restaurant {restaurant_id} not found")

    new_cart = create_cart(restaurant_id, g.user_id)
    session["cart_id"] = new_cart.id
    return created_response(serialize_cart(new_cart))


@bp.post("/<int:cart_id>/items")
@require_auth(["customer"])
def add_item_to_cart_endpoint():
    """
    Adds a single item to an existing cart.

    This is step 2 of the new checkout flow. Can be called multiple times
    to add different items.
    """
    cart = resolve_trusted_cart()
    item_id_int = require_int_param("item_id")

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

    add_item_to_cart(cart.id, item_id_int)
    return success_response(serialize_cart(cart))


def charge_customer_with_hold(checkout_handler):
    @wraps(checkout_handler)
    def decorated_function():
        """Authorize funds up-front and expose checkout context to the handler."""
        cart = resolve_trusted_cart()
        tip = abs(get_decimal_param("tip", Decimal("0.00")))

        # Cart must exist and have items
        cart_items = get_cart_items(cart.id)
        require_condition(cart_items, f"Cart {cart.id} is empty")

        # Calculate the total amount of the cart
        subtotal, delivery_fee = calculate_cart_price(cart_items)
        require_condition(subtotal, f"Cart {cart.id} is empty")

        # Ensure the customer has enough balance
        total_amount = subtotal + delivery_fee + tip
        require_condition(g.balance >= total_amount, "Insufficient balance")

        # Prevent cart reuse once checkout starts
        session.pop("cart_id", None)

        # Funds are deducted inside the open request transaction. If anything
        # raises afterwards, the teardown handler will roll back and release
        # the hold automatically.
        charge_user(g.user_id, total_amount)

        try:
            return checkout_handler(delivery_fee, tip, total_amount)
        finally:
            g.pop("checkout_context", None)

    return decorated_function


@bp.post("/<int:cart_id>/checkout")
@require_auth(["customer"])
@charge_customer_with_hold
def checkout_cart(delivery_fee: Decimal, tip: Decimal, total_amount: Decimal):
    """Checks out a cart and creates an order."""
    delivery_address = get_param("delivery_address") or ""
    cart = resolve_trusted_cart()
    cart_items = get_cart_items(cart.id)
    require_condition(cart_items, f"Cart {cart.id} is empty")

    # Create the order and its order items
    order, order_items = create_order_from_checkout(
        user_id=g.user_id,
        restaurant_id=cart.restaurant_id,
        total=total_amount,
        cart_items=cart_items,
        delivery_fee=delivery_fee,
        delivery_address=delivery_address,
        tip=tip,
    )
    save_order_securely(order, order_items)

    return created_response(serialize_order(order))
