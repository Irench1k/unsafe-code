from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import GroupMember, User


class UserRepository:
    def __init__(self, session: Session):
        self.s = session

    def create_user(self, email: str, first_name: str, last_name: str, password_hash: str) -> User:
        user = User(email=email, first_name=first_name, last_name=last_name, password_hash=password_hash)
        self.s.add(user)
        self.s.flush()
        return user

    def get_by_email(self, email: str) -> User | None:
        """Get user by email address"""
        stmt = select(User).where(User.email == email)
        return self.s.scalars(stmt).first()

    def get_by_username(self, username: str) -> User | None:
        """Get user by username (alias for email for compatibility)"""
        return self.get_by_email(username)

    def list_users_for_domain(self, domain: str) -> list[User]:
        """Get all users for a domain"""
        stmt = select(User).where(User.email.ilike(f'%@{domain}'))
        # Other ideas:
        # where(User.email.op('~*')(rf'@{domain}'))
        # where(func.lower(func.split_part(User.email, '@', 2)) == domain.lower())
        # where(User.email.endswith(f'@{domain}'))
        return list(self.s.scalars(stmt).all())

    def is_group_member(self, user_email: str, group_name: str) -> bool:
        """Check if user is member of group"""
        stmt = select(GroupMember).where(
            (GroupMember.user_email == user_email) &
            (GroupMember.group_name == group_name)
        )
        return self.s.scalars(stmt).first() is not None

    def is_group_admin(self, user_email: str, group_name: str) -> bool:
        """Check if user is admin of group"""
        stmt = select(GroupMember).where(
            (GroupMember.user_email == user_email) &
            (GroupMember.group_name == group_name) &
            (GroupMember.role == "admin")
        )
        return self.s.scalars(stmt).first() is not None
