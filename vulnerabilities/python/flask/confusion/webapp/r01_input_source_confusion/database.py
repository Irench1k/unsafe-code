import datetime
from decimal import Decimal
from typing import List

from pydantic import BaseModel, Field


class MenuItem(BaseModel):
    id: str
    name: str
    price: Decimal
    available: bool


class OrderItem(BaseModel):
    item_id: str
    name: str
    price: Decimal


class Order(BaseModel):
    order_id: str
    total: Decimal
    user_id: str
    created_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)
    items: List[OrderItem]


class User(BaseModel):
    user_id: str
    email: str
    name: str
    balance: Decimal
    password: str


db = {
    "menu_items": {
        "1": MenuItem(id="1", name="Krabby Patty", price=Decimal("5.99"), available=True),
        "2": MenuItem(id="2", name="Krusty Krab Pizza", price=Decimal("12.50"), available=True),
        "3": MenuItem(id="3", name="Side of Fries", price=Decimal("1.00"), available=True),
        "4": MenuItem(id="4", name="Kelp Shake", price=Decimal("2.50"), available=True),
    },
    "users": {
        "sandy": User(
            user_id="sandy",
            email="sandy.cheeks@bikinibottom.com",
            name="Sandy Cheeks",
            balance=Decimal("50.00"),
            password="testpassword",
        ),
        "spongebob": User(
            user_id="spongebob",
            email="spongebob.squarepants@bikinibottom.com",
            name="SpongeBob SquarePants",
            balance=Decimal("20.00"),
            password="i_l0ve_burg3rs",
        ),
    },
    "orders": {},
    "next_order_id": 1,
}


def get_menu_item(item_id: str) -> MenuItem | None:
    return db["menu_items"].get(item_id)


def get_user(user_id: str) -> User | None:
    return db["users"].get(user_id)


def charge_user(user_id: str, amount: Decimal):
    user = get_user(user_id)
    if not user:
        raise ValueError(f"User '{user_id}' not found.")
    if user.balance < amount:
        raise ValueError("Insufficient funds.")
    user.balance -= amount


def create_order(order: Order):
    db["orders"][order.order_id] = order
    db["next_order_id"] += 1


def get_next_order_id() -> str:
    return str(db["next_order_id"])
