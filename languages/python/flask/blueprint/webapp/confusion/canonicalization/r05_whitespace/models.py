import enum
from datetime import datetime

from sqlalchemy import (CheckConstraint, DateTime, Enum, Integer, String, Text,
                        func)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# ---------- Base ----------

class Base(DeclarativeBase):
    pass


# ---------- Enums ----------

class RoleEnum(str, enum.Enum):
    member = "member"
    admin = "admin"


# ---------- Organization ----------
# Simple table - organizations are identified by domain
class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    domain: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    owner_email: Mapped[str] = mapped_column(String(255), nullable=False)


# ---------- Users ----------
# Users are matched to orgs by email domain
class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # Store email as the primary identifier (like r04 'name' field)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    first_name: Mapped[str] = mapped_column(String(128), nullable=False)
    last_name: Mapped[str] = mapped_column(String(128), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(256), nullable=False)


# ---------- Groups ----------
# Groups are matched to orgs by email domain in group name
class Group(Base):
    __tablename__ = "groups"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # Group name includes domain (e.g., "staff@krusty-krab.sea")
    name: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)


# ---------- Group membership ----------
class GroupMember(Base):
    __tablename__ = "group_members"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # Store actual email addresses
    user_email: Mapped[str] = mapped_column(String(255), nullable=False)
    group_name: Mapped[str] = mapped_column(String(128), nullable=False)
    role: Mapped[RoleEnum] = mapped_column(
        Enum(RoleEnum, name="role_enum"), nullable=False, server_default="member"
    )


# ---------- Messages ----------
class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # Store email addresses directly
    from_user: Mapped[str] = mapped_column(String(255), nullable=False)

    # For group messages, store group name; for user messages, store user email
    recipient_group: Mapped[str | None] = mapped_column(String(128), nullable=True)
    recipient_user: Mapped[str | None] = mapped_column(String(255), nullable=True)

    message: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # Either recipient_group or recipient_user must be set
    __table_args__ = (
        CheckConstraint(
            func.num_nonnulls(recipient_group, recipient_user) == 1,
            name="check_recipient_group_or_recipient_user",
        ),
    )
