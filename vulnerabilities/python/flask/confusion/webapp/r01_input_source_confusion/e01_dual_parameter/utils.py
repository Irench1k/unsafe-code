from decimal import Decimal

from .database import get_menu_item
from .models import OrderItem


def check_price_and_availability(form_data):
    """Checks the price and availability of an item."""
    # Now we expect to see "items" in the body form, but
    # "item" parameter is still accepted, so we need to process it as well!
    if "item" in form_data:
        item_id = form_data.get("item")
        if not item_id:
            return None
        menu_item = get_menu_item(item_id)
        if not menu_item:
            return None
        if not menu_item.available:
            return None
        return menu_item.price

    # If "items" are passed in the body form
    item_ids = form_data.getlist("items")
    if not item_ids:
        return None

    total_price = Decimal("0.0")
    for item_id in item_ids:
        if not item_id:
            continue
        menu_item = get_menu_item(item_id)
        if not menu_item:
            return None
        total_price += menu_item.price

    return total_price


def get_order_items(form_data):
    """
    Converts menu item IDs to OrderItem objects.

    The menu item price might change during or after the order is created,
    so we need to record this information properly.
    """
    item_ids = form_data.getlist("items")
    # If "items" parameter is missing, check if "item" parameter is present
    if not item_ids:
        item_id = form_data.get("item")
        if not item_id:
            return None
        item_ids = [item_id]

    order_items = []
    for item_id in item_ids:
        if not item_id:
            continue
        menu_item = get_menu_item(item_id)
        if not menu_item:
            return None
        order_items.append(OrderItem(item_id=item_id, name=menu_item.name, price=menu_item.price))

    return order_items
