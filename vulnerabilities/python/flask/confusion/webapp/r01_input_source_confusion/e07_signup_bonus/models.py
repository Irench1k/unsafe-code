import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field


# Helper function to avoid importing database module in the models module (resolve circular imports)
def get_next_order_id_from_db() -> str:
    from .database import get_next_order_id

    return get_next_order_id()


def get_next_refund_id_from_db() -> str:
    from .database import get_next_refund_id

    return get_next_refund_id()


class MenuItem(BaseModel):
    id: str
    name: str
    price: Decimal
    available: bool


class OrderItem(BaseModel):
    item_id: str
    name: str
    price: Decimal


# Either create a new Model OrderRequest without order_id param, or add a Field(default_factory=...) to the existing order_id
class Order(BaseModel):
    order_id: str = Field(default_factory=get_next_order_id_from_db)
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
    refund_id: str = Field(default_factory=get_next_refund_id_from_db)
    order_id: str
    amount: Decimal
    reason: str = Field(default="")
    status: Literal["pending", "auto_approved", "rejected"] = Field(default="pending")
    auto_approved: bool
    created_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)


class User(BaseModel):
    user_id: str
    name: str
    balance: Decimal = Field(default=Decimal("0.00"))
    password: str
