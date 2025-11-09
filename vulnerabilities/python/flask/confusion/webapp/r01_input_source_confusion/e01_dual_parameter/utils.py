from decimal import Decimal

from .database import get_menu_item
from .models import OrderItem


def _check_price_and_availability_v100(item_id):
    """Checks the price and availability of an item."""
    if not item_id:
        return None

    menu_item = get_menu_item(item_id)
    if not menu_item:
        return None

    if not menu_item.available:
        return None

    return menu_item.price


def check_price_and_availability(data):
    """Checks the price and availability of items added to the cart."""
    if "item" in data:  # noqa: SIM108
        items = [data.get("item")]
    else:
        items = data.getlist("items")

    total_price = Decimal(0)
    for item in items:
        price = _check_price_and_availability_v100(item)
        if not price:
            return None
        total_price += price

    return total_price


def _get_order_items_v100(item_id):
    """
    Converts single menu item ID to OrderItem objects.

    The menu item price might change during or after the order is created,
    so we need to record this information properly.
    """
    menu_item = get_menu_item(item_id)
    if not menu_item:
        return None

    return [OrderItem(item_id=item_id, name=menu_item.name, price=menu_item.price)]


def get_order_items(form_data):
    """Builds OrderItem list for order creation method."""
    item_ids = form_data.getlist("items") or [form_data.get("item")]

    order_items = []
    for item_id in item_ids:
        new_items = _get_order_items_v100(item_id)
        order_items.extend(new_items)

    return order_items
