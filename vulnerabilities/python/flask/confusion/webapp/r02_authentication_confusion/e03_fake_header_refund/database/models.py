"""
Data Models

Pure Pydantic models with no database access.
These represent the structure of our data entities.
"""

import datetime
from decimal import Decimal
from typing import Literal

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
    delivery_address: str
    tip: Decimal = Field(default=Decimal("0.00"))


class Cart(BaseModel):
    cart_id: str
    items: list[str]  # Array of item IDs


class Refund(BaseModel):
    refund_id: str
    order_id: str
    amount: Decimal
    reason: str = Field(default="")
    status: Literal["pending", "auto_approved", "approved", "rejected"] = Field(default="pending")
    auto_approved: bool
    paid: bool = Field(default=False)
    created_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)


class User(BaseModel):
    user_id: str
    name: str
    balance: Decimal = Field(default=Decimal("0.00"))
    password: str
