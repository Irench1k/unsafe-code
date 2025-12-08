"""Restaurant Service - business logic for restaurant operations."""

import uuid

from ..database.models import MenuItem, Restaurant
from ..database.repository import (
    save_menu_item,
    save_restaurant,
)


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
