from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Message


class MessageRepository:
    def __init__(self, session: Session):
        self.s = session

    def _create_message(self, from_user: str, message: str, recipient_group: str = "", recipient_user: str = "") -> Message:
        """Create a message using email addresses"""
        msg = Message(
            from_user=from_user,
            message=message,
            recipient_group=recipient_group,
            recipient_user=recipient_user
        )
        self.s.add(msg)
        self.s.flush()
        return msg

    def send_to_user(self, from_user: str, recipient_user: str, message: str) -> Message:
        """Send message to a user - using email addresses"""
        return self._create_message(
            from_user=from_user,
            message=message,
            recipient_user=recipient_user
        )

    def send_to_group(self, from_user: str, recipient_group: str, message: str) -> Message:
        """Send message to a group - using group name"""
        return self._create_message(
            from_user=from_user,
            message=message,
            recipient_group=recipient_group
        )

    def get_user_messages(self, user_email: str) -> list[Message]:
        """Get messages sent to a specific user"""
        stmt = select(Message).where(Message.recipient_user == user_email)
        return list(self.s.scalars(stmt).all())

    def get_group_messages(self, group_name: str) -> list[Message]:
        """Get messages sent to a specific group"""
        stmt = select(Message).where(Message.recipient_group == group_name)
        return list(self.s.scalars(stmt).all())

    def get_messages_from_user(self, user_email: str) -> list[Message]:
        """Get all messages sent by a user"""
        stmt = select(Message).where(Message.from_user == user_email)
        return list(self.s.scalars(stmt).all())

    def get_messages_for_domain(self, domain: str) -> list[Message]:
        """Get all messages for users/groups in a domain"""
        stmt = select(Message).where(
            (Message.from_user.ilike(f'%@{domain}')) |
            (Message.recipient_user.ilike(f'%@{domain}')) |
            (Message.recipient_group.ilike(f'%@{domain}'))
        )
        return list(self.s.scalars(stmt).all())
