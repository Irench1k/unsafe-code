from .database import get_menu_item
from .models import OrderItem

def check_price_and_availability(item_id):
    """Checks the price and availability of an item."""
    if not item_id:
        return None

    menu_item = get_menu_item(item_id)
    if not menu_item:
        return None

    if not menu_item.available:
        return None

    return menu_item.price


def get_order_items(form_data):
    """
    Converts menu item IDs to OrderItem objects.

    The menu item price might change during or after the order is created,
    so we need to record this information properly.
    """
    item_id = form_data.get("item")
    menu_item = get_menu_item(item_id)
    order_items = [OrderItem(item_id=item_id, name=menu_item.name, price=menu_item.price)]

    return order_items
