"""Restaurant Service - business logic for restaurant operations."""

import logging
import uuid

from ..database.models import MenuItem, OrderStatus, Restaurant
from ..database.repository import (
    any_order_belongs_to_restaurant,
    find_order_by_id,
    get_refund_by_order_id,
    save_menu_item,
    save_restaurant,
)
from ..database.services import create_refund, find_order_owner, process_refund
from ..errors import CheekyApiError

logger = logging.getLogger(__name__)


# ============================================================
# RESTAURANT OPERATIONS
# ============================================================
def create_restaurant(name: str, description: str, domain: str, owner: str) -> Restaurant:
    """Creates a new restaurant with auto-generated API key."""
    api_key = f"key-{domain.replace('.', '-')}-{uuid.uuid4()}"
    restaurant = Restaurant(
        name=name,
        description=description or f"Welcome to {name}!",
        domain=domain,
        owner=owner,
        api_key=api_key,
    )
    save_restaurant(restaurant)
    logger.info(f"Restaurant created: {restaurant.id} - {name}")
    return restaurant


def update_restaurant(
    restaurant: Restaurant,
    name: str | None = None,
    description: str | None = None,
    domain: str | None = None,
) -> Restaurant:
    """Updates a restaurant profile."""
    restaurant.name = name or restaurant.name
    restaurant.description = description or restaurant.description
    restaurant.domain = domain or restaurant.domain
    save_restaurant(restaurant)
    return restaurant


# ============================================================
# MENU ITEM OPERATIONS
# ============================================================
def create_menu_item_for_restaurant(restaurant_id: int, fields: dict) -> MenuItem:
    """Create and persist a menu item for a restaurant."""
    allowed = {"name", "price", "available"}
    payload = {key: fields[key] for key in allowed if key in fields}
    payload.setdefault("available", True)
    menu_item = MenuItem(restaurant_id=restaurant_id, **payload)
    save_menu_item(menu_item)
    return menu_item


def apply_menu_item_changes(menu_item: MenuItem, fields: dict) -> MenuItem:
    """Apply validated field updates and persist the menu item."""
    allowed = {"name", "price", "available"}
    for field in allowed:
        if field in fields:
            setattr(menu_item, field, fields[field])
    save_menu_item(menu_item)
    return menu_item


# ============================================================
# BATCH REFUND OPERATIONS
# ============================================================
def process_batch_refund(
    restaurant_id: int, order_ids: list[int], reason: str
) -> tuple[list[int], list[dict]]:
    """
    Process batch refund request for multiple orders.

    Restaurant managers can proactively refund orders before customers complain,
    useful for handling quality issues, delivery problems, or promotional goodwill.

    Returns: (processed_ids, skipped_ids)
    """
    # Verify the restaurant has at least one legitimate order in the batch
    if not any_order_belongs_to_restaurant(order_ids, restaurant_id):
        raise CheekyApiError("No orders found for this restaurant in the batch")

    processed_ids: list[int] = []
    skipped_ids: list[dict] = []

    # Process each order in the batch
    for order_id in order_ids:
        order = find_order_by_id(order_id)

        # Skip if order not found
        if not order:
            skipped_ids.append({"order_id": order_id, "reason": "Order not found"})
            continue

        # Skip if order already has a refund
        existing_refund = get_refund_by_order_id(order_id)
        if existing_refund:
            skipped_ids.append({"order_id": order_id, "reason": "Already refunded"})
            continue

        # Skip if order is not in delivered status
        if order.status != OrderStatus.delivered:
            skipped_ids.append({
                "order_id": order_id,
                "reason": f"Order status is {order.status.value}, must be delivered"
            })
            continue

        # Create and process the refund (auto-approved for restaurant-initiated refunds)
        refund = create_refund(
            order_id=order_id,
            amount=order.total,
            reason=reason,
            auto_approved=True,
        )

        # Credit the customer
        order_owner = find_order_owner(order_id)
        if order_owner:
            process_refund(refund, order_owner)
            order.status = OrderStatus.refunded
            processed_ids.append(order_id)
            logger.info(f"Batch refund processed: order {order_id} for restaurant {restaurant_id}")
        else:
            skipped_ids.append({"order_id": order_id, "reason": "Order owner not found"})

    return processed_ids, skipped_ids
