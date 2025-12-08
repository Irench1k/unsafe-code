"""
SQLAlchemy ORM Models

These models map to PostgreSQL tables and handle data persistence.
Note: Constraints are intentionally minimal to allow for authorization
confusion vulnerabilities in this educational context.
"""

import datetime
import enum
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for all ORM models."""

    pass


class RefundStatus(enum.Enum):
    """Enumeration for refund statuses."""

    pending = "pending"
    approved = "approved"
    rejected = "rejected"


class Restaurant(Base):
    """Restaurant model - represents a restaurant in the system."""

    __tablename__ = "restaurants"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=False, default="")
    owner: Mapped[str] = mapped_column(String, nullable=False)
    api_key: Mapped[str] = mapped_column(String, nullable=False)
    domain: Mapped[str] = mapped_column(String, nullable=False)


class User(Base):
    """User model - represents a customer in the system."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    balance: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        CheckConstraint("balance >= 0", name="user_balance_non_negative"),
        nullable=False,
        default=Decimal("0.00"),
    )
    password: Mapped[str] = mapped_column(String, nullable=False)


class MenuItem(Base):
    """Menu item model - represents an item on a restaurant's menu."""

    __tablename__ = "menu_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    restaurant_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("restaurants.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    price: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        CheckConstraint("price > 0", name="menu_item_price_positive"),
        nullable=False,
    )
    available: Mapped[bool] = mapped_column(nullable=False, default=True)


class OrderStatus(enum.Enum):
    """Enumeration for order statuses."""

    created = "created"  # Order has been created and paid by customer
    delivered = "delivered"  # Order has been delivered to customer
    refunded = "refunded"  # Order has been refunded
    cancelled = "cancelled"  # Order has been cancelled by customer or restaurant manager


class Order(Base):
    """Order model - represents a customer order."""

    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    restaurant_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("restaurants.id"), nullable=False
    )
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    total: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        CheckConstraint("total >= 0", name="order_total_non_negative"),
        nullable=False,
    )
    delivery_fee: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        CheckConstraint("delivery_fee >= 0", name="order_delivery_fee_non_negative"),
        nullable=False,
    )
    delivery_address: Mapped[str] = mapped_column(String, nullable=False)
    tip: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        CheckConstraint("tip >= 0", name="order_tip_non_negative"),
        nullable=False,
        default=Decimal("0.00"),
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.datetime.utcnow
    )

    status: Mapped[OrderStatus] = mapped_column(
        Enum(OrderStatus), nullable=False, default=OrderStatus.created
    )


class OrderItem(Base):
    """Order item model - represents an item in an order."""

    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(Integer, ForeignKey("orders.id"), nullable=False)
    item_id: Mapped[int] = mapped_column(Integer, ForeignKey("menu_items.id"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    price: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        CheckConstraint("price > 0", name="order_item_price_positive"),
        nullable=False,
    )
    coupon_id: Mapped[int] = mapped_column(Integer, ForeignKey("coupons.id"), nullable=True)


class Cart(Base):
    """Cart model - represents a shopping cart."""

    __tablename__ = "carts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    restaurant_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("restaurants.id"), nullable=False
    )
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    active: Mapped[bool] = mapped_column(nullable=False, default=True)


class CartItem(Base):
    """Cart item model - represents an item in a shopping cart."""

    __tablename__ = "cart_items"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    cart_id: Mapped[int] = mapped_column(Integer, ForeignKey("carts.id"), nullable=False)
    item_id: Mapped[int] = mapped_column(Integer, ForeignKey("menu_items.id"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    coupon_id: Mapped[int] = mapped_column(Integer, ForeignKey("coupons.id"), nullable=True)


class CouponType(enum.Enum):
    """Enumeration for coupon types."""

    discount_percent = "discount_percent"
    fixed_amount = "fixed_amount"
    free_item_sku = "free_item_sku"


class Coupon(Base):
    """Coupon model - represents a coupon code."""

    __tablename__ = "coupons"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String, nullable=False)
    type: Mapped[CouponType] = mapped_column(Enum(CouponType), nullable=False)
    value: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=True)
    restaurant_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("restaurants.id"), nullable=False
    )
    item_id: Mapped[int] = mapped_column(Integer, ForeignKey("menu_items.id"), nullable=False)


class Refund(Base):
    """Refund model - represents a refund request."""

    __tablename__ = "refunds"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(Integer, ForeignKey("orders.id"), nullable=False)
    amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        CheckConstraint("amount > 0", name="refund_amount_positive"),
        nullable=False,
    )
    reason: Mapped[str] = mapped_column(String, nullable=False, default="")
    status: Mapped[RefundStatus] = mapped_column(
        Enum(RefundStatus), nullable=False, default=RefundStatus.pending
    )
    auto_approved: Mapped[bool] = mapped_column(nullable=False, default=False)
    paid: Mapped[bool] = mapped_column(nullable=False, default=False)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.datetime.utcnow
    )


class PlatformConfig(Base):
    """Platform configuration - stores platform-wide settings."""

    __tablename__ = "platform_config"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    key: Mapped[str] = mapped_column(String, nullable=False)
    value: Mapped[str] = mapped_column(String, nullable=False)
