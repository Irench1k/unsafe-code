from sqlalchemy import select
from sqlalchemy.orm import Session
from ..models import Group, Message, User


class MessageRepository:
    def __init__(self, session: Session):
        self.s = session

    # Create

    def send_to_user(
        self, author_email: str, recipient_user_email: str, body: str
    ) -> Message:
        msg = Message(
            author=User(email=author_email),
            recipient_user=User(email=recipient_user_email),
            body=body,
        )
        self.s.add(msg)
        self.s.flush()
        return msg

    def send_to_group(
        self, author_email: str, recipient_group_name: str, body: str
    ) -> Message:
        msg = Message(
            author=User(email=author_email),
            recipient_group=Group(name=recipient_group_name),
            body=body,
        )
        self.s.add(msg)
        self.s.flush()
        return msg

    # Query by sender

    def by_sender(self, email: str, limit: int = 100, offset: int = 0) -> list[Message]:
        stmt = (
            select(Message)
            .where(Message.author.has(User.email == email))
            .order_by(Message.created_at.desc())
            .limit(limit).offset(offset)
        )
        return list(self.s.scalars(stmt).all())

    # Inbox / destination

    def to_user(self, email: str, limit: int = 100, offset: int = 0) -> list[Message]:
        stmt = (
            select(Message)
            .where(Message.recipient_user.has(User.email == email))
            .order_by(Message.created_at.desc())
            .limit(limit).offset(offset)
        )
        return list(self.s.scalars(stmt).all())

    def to_group(self, group_name: str, limit: int = 100, offset: int = 0) -> list[Message]:
        stmt = (
            select(Message)
            .where(Message.recipient_group.has(Group.name == group_name))
            .order_by(Message.created_at.desc())
            .limit(limit).offset(offset)
        )
        return list(self.s.scalars(stmt).all())
