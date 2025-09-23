from __future__ import annotations

from datetime import datetime
import enum

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


# ---------- Base ----------

class Base(DeclarativeBase):
    pass


# ---------- Enums ----------

class RoleEnum(str, enum.Enum):
    member = "member"
    admin = "admin"


# ---------- Organization ----------

class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    domain: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    owner_email: Mapped[str] = mapped_column(String(255), nullable=False)

    # ORM relations
    users: Mapped[list["User"]] = relationship(back_populates="organization", cascade="all, delete-orphan")
    groups: Mapped[list["Group"]] = relationship(back_populates="organization", cascade="all, delete-orphan")


# ---------- Users ----------

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    username: Mapped[str] = mapped_column(String(128), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    first_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    password_hash: Mapped[str] = mapped_column(String(256), nullable=False)

    # ORM relations
    organization: Mapped[Organization] = relationship(back_populates="users")

    # messages authored by this user
    messages_authored: Mapped[list["Message"]] = relationship(
        back_populates="author", cascade="all, delete-orphan"
    )

    # private messages received by this user
    messages_received: Mapped[list["Message"]] = relationship(
        back_populates="recipient_user",
        primaryjoin="User.id == Message.recipient_user_id",
        viewonly=True,  # we write via Message, we read here
    )

    # groups this user belongs to, with roles via association object
    member_links: Mapped[list["GroupMember"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )

    # convenience: groups list (viewonly) if you just want the groups
    groups: Mapped[list["Group"]] = relationship(
        secondary="group_members", viewonly=True, back_populates="users"
    )

    __table_args__ = (
        UniqueConstraint("organization_id", "username", name="uq_user_org_username"),
        UniqueConstraint("organization_id", "email", name="uq_user_org_email"),
        Index("ix_users_org", "organization_id"),
    )


# ---------- Groups ----------

class Group(Base):
    __tablename__ = "groups"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ORM relations
    organization: Mapped[Organization] = relationship(back_populates="groups")

    # messages sent to this group
    messages: Mapped[list["Message"]] = relationship(
        back_populates="recipient_group", primaryjoin="Group.id == Message.recipient_group_id",
        viewonly=True
    )

    # membership links and convenience list of users
    member_links: Mapped[list["GroupMember"]] = relationship(
        back_populates="group", cascade="all, delete-orphan"
    )
    users: Mapped[list["User"]] = relationship(
        secondary="group_members", viewonly=True, back_populates="groups"
    )

    __table_args__ = (
        UniqueConstraint("organization_id", "name", name="uq_group_org_name"),
        Index("ix_groups_org", "organization_id"),
    )


# ---------- Group membership (association object) ----------

class GroupMember(Base):
    __tablename__ = "group_members"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    group_id: Mapped[int] = mapped_column(
        ForeignKey("groups.id", ondelete="CASCADE"), primary_key=True
    )
    role: Mapped[RoleEnum] = mapped_column(
        Enum(RoleEnum, name="role_enum"), nullable=False, server_default="member"
    )

    # ORM relations
    user: Mapped[User] = relationship(back_populates="member_links")
    group: Mapped[Group] = relationship(back_populates="member_links")

    __table_args__ = (
        # Helpful when you often filter by group or user
        Index("ix_group_members_group", "group_id"),
        Index("ix_group_members_user", "user_id"),
    )


# ---------- Messages (single table for both kinds) ----------

class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )

    # who sent it
    author_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    # recipient: exactly one of these must be non-null
    recipient_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=True
    )
    recipient_group_id: Mapped[int | None] = mapped_column(
        ForeignKey("groups.id", ondelete="CASCADE"), nullable=True
    )

    body: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),  # db clock, tz-aware
    )

    # ORM relations
    author: Mapped[User] = relationship(back_populates="messages_authored", foreign_keys=[author_id])

    recipient_user: Mapped[User | None] = relationship(
        foreign_keys=[recipient_user_id],
        back_populates="messages_received",
    )

    recipient_group: Mapped[Group | None] = relationship(
        foreign_keys=[recipient_group_id],
        back_populates="messages",
    )

    __table_args__ = (
        # enforce XOR recipient (exactly one non-null)
        CheckConstraint(
            "(recipient_user_id IS NOT NULL) <> (recipient_group_id IS NOT NULL)",
            name="ck_messages_one_recipient",
        ),
        Index("ix_messages_org_author_created", "organization_id", "author_id", "created_at"),
        Index("ix_messages_org_recv_user_created", "organization_id", "recipient_user_id", "created_at"),
        Index("ix_messages_org_recv_group_created", "organization_id", "recipient_group_id", "created_at"),
    )
