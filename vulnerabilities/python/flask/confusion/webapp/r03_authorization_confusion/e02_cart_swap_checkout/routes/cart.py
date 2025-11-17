from decimal import Decimal
from functools import wraps

from flask import Blueprint, g, session

from ..auth.decorators import require_auth
from ..database.repository import find_cart_by_id, find_menu_item_by_id, get_cart_items
from ..database.services import (
    add_item_to_cart,
    calculate_cart_price,
    charge_user,
    create_cart,
    create_order_from_checkout,
    refund_user,
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
        # TODO: Replace cart ID with authorized cart object
        # values["cart"] = resolve_trusted_cart()


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
    if session:
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
    def decorated_function(*args, **kwargs):
        """
        Charge customer before checkout flows and keep the transaction scoped here.
        """
        cart = resolve_trusted_cart()
        require_condition(g.db_session, "Database session required for checkout")

        g.tip = abs(get_decimal_param("tip", Decimal("0.00")))
        charged_amount = Decimal("0.00")

        transaction = g.db_session.begin()
        try:
            cart_items = get_cart_items(cart.id)
            require_condition(cart_items, f"Cart {cart.id} is empty")

            g.subtotal, g.delivery_fee = calculate_cart_price(cart_items)
            require_condition(g.subtotal, f"Cart {cart.id} is empty")

            total_amount = g.subtotal + g.delivery_fee + g.tip
            require_condition(g.balance >= total_amount, "Insufficient balance")

            # Validations passed, charged
            session.pop("cart_id")
            charge_user(g.user_id, total_amount)

            # TODO: check this
            charged_amount = total_amount

            # Execute the checkout handler to place the order
            result = checkout_handler(*args, **kwargs)
            transaction.commit()
            return result
        except Exception:
            if transaction.is_active:
                transaction.rollback()
            # TODO: Is this correct? Looks like double refund potentially, check dynamically
            if charged_amount:
                refund_user(g.user_id, charged_amount)
            raise
        finally:
            if transaction.is_active:
                transaction.rollback()

    return decorated_function


@bp.post("/<int:cart_id>/checkout")
@require_auth(["customer"])
@charge_customer_with_hold
def checkout_cart():
    """Checks out a cart and creates an order."""
    # Parse inputs
    delivery_address = get_param("delivery_address") or ""

    # Fetch and validate cart
    cart = resolve_trusted_cart()

    # Get cart items from the database
    cart_items = get_cart_items(cart.id)
    require_condition(cart_items, f"Cart {cart.id} is empty")

    # Integrity check: user must have sufficient balance
    total_amount = g.subtotal + g.delivery_fee + g.tip
    require_condition(g.balance >= total_amount, "Insufficient balance")

    # Create and save order
    order, order_items = create_order_from_checkout(
        user_id=g.user_id,
        restaurant_id=cart.restaurant_id,
        total=total_amount,
        cart_items=cart_items,
        delivery_fee=g.delivery_fee,
        delivery_address=delivery_address,
        tip=g.tip,
    )

    save_order_securely(order, order_items)
    return created_response(serialize_order(order))
