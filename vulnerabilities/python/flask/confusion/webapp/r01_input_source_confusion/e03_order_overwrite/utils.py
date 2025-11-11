from decimal import Decimal
from typing import List

from .database import get_menu_item
from .models import OrderItem

DELIVERY_FEE = Decimal("5.00")
FREE_DELIVERY_ABOVE = Decimal("25.00")


def _check_price_and_availability_v100(item_id):
    """Checks the price and availability of a single item."""
    if not item_id:
        return None

    menu_item = get_menu_item(item_id)
    if not menu_item:
        return None

    if not menu_item.available:
        return None

    return menu_item.price


def _calculate_total_price(item_ids: List[str]) -> Decimal | None:
    """
    Core logic: calculates total price for a list of item IDs.
    Returns None if any item is unavailable.
    """
    total_price = Decimal("0.00")
    for item_id in item_ids:
        price = _check_price_and_availability_v100(item_id)
        if not price:
            return None
        total_price += price
    return total_price


def _calculate_delivery_fee_for_total(total_price: Decimal) -> Decimal:
    """
    Core logic: determines delivery fee based on order total.
    Free delivery for orders above $25.00.
    """
    if total_price > FREE_DELIVERY_ABOVE:
        return Decimal("0.00")
    return DELIVERY_FEE


def convert_item_ids_to_order_items(item_ids: List[str]) -> List[OrderItem]:
    """
    Core logic: converts item IDs to OrderItem objects with locked-in prices.

    The menu item price might change during or after the order is created,
    so we snapshot the current price at order time.
    """
    order_items = []
    for item_id in item_ids:
        menu_item = get_menu_item(item_id)
        if menu_item:
            order_items.append(
                OrderItem(item_id=item_id, name=menu_item.name, price=menu_item.price)
            )
    return order_items


# ============================================================
# OLD FLOW: POST /orders (form-based, v102 - fixed from e02)
# ============================================================


def check_price_and_availability(data):
    """Checks the price and availability of items from form data."""
    items = data.getlist("items")
    return _calculate_total_price(items)


def calculate_delivery_fee(data):
    """Calculates delivery fee for the old POST /orders endpoint."""
    price = check_price_and_availability(data)
    if not price:
        return DELIVERY_FEE
    return _calculate_delivery_fee_for_total(price)


def get_order_items(data):
    """Builds OrderItem list from form data for the old POST /orders endpoint."""
    item_ids = data.getlist("items")
    return convert_item_ids_to_order_items(item_ids)


# ============================================================
# NEW FLOW: Cart-based checkout (v103+)
# ============================================================


def check_cart_price_and_delivery_fee(item_ids: List[str]) -> tuple[Decimal, Decimal]:
    """Checks the price and availability of items in a cart."""
    total_price = _calculate_total_price(item_ids)
    if not total_price:
        return None, None
    delivery_fee = _calculate_delivery_fee_for_total(total_price)
    return total_price, delivery_fee
