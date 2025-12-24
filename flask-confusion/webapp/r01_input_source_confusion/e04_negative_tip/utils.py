from collections.abc import Iterable
from decimal import Decimal

from .database import get_menu_item
from .models import OrderItem

DELIVERY_FEE = Decimal("5.00")
FREE_DELIVERY_ABOVE = Decimal("25.00")


def _menu_item_price(item_id: str) -> Decimal | None:
    """Returns the current price for an available menu item."""
    if not item_id:
        return None

    menu_item = get_menu_item(item_id)
    if not menu_item or not menu_item.available:
        return None

    return menu_item.price


def _calculate_delivery_fee(total_price: Decimal) -> Decimal:
    """Adds a flat delivery fee unless the order crosses the free-shipping threshold."""
    if total_price > FREE_DELIVERY_ABOVE:
        return Decimal("0.00")
    return DELIVERY_FEE


def check_cart_price_and_delivery_fee(item_ids: Iterable[str]) -> tuple[Decimal, Decimal]:
    """
    Validates that all cart items are orderable and returns their price and delivery fee.

    Returns (None, None) as a signal to the caller when any menu item is missing or unavailable.
    """
    total_price = Decimal("0.00")
    for item_id in item_ids:
        price = _menu_item_price(item_id)
        if price is None:
            return None, None
        total_price += price

    return total_price, _calculate_delivery_fee(total_price)


def convert_item_ids_to_order_items(item_ids: Iterable[str]) -> list[OrderItem]:
    """
    Converts item IDs to OrderItem snapshots so invoices stay stable even if prices change later.
    """
    order_items: list[OrderItem] = []
    for item_id in item_ids:
        menu_item = get_menu_item(item_id)
        if not menu_item:
            continue
        order_items.append(OrderItem(item_id=item_id, name=menu_item.name, price=menu_item.price))
    return order_items
