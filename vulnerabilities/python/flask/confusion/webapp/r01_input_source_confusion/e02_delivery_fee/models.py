import datetime
from decimal import Decimal

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
    items: list[OrderItem]
    delivery_fee: Decimal


class User(BaseModel):
    user_id: str
    email: str
    name: str
    balance: Decimal
    password: str
