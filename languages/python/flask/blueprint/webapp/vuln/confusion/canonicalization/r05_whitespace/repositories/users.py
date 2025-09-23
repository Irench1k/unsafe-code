from sqlalchemy import select, and_
from sqlalchemy.orm import Session
from ..models import User, GroupMember


class UserRepository:
    def __init__(self, session: Session):
        self.s = session
  
    def create_user(self, email: str, first_name: str, last_name: str, password_hash: str) -> User:
        user = User(email=email, first_name=first_name, last_name=last_name, password_hash=password_hash)
        self.s.add(user)
        self.s.flush()
        return user

    def get_by_username(self, org_id: int, username: str) -> User | None:
        stmt = select(User).where(
            and_(User.organization_id == org_id, User.username == username)
        )
        return self.s.scalars(stmt).first()

    def get_by_email(self, org_id: int, email: str) -> User | None:
        stmt = select(User).where(
            and_(User.organization_id == org_id, User.email == email)
        )
        return self.s.scalars(stmt).first()

    def list_group_members(self, org_id: int, group_id: int) -> list[User]:
        stmt = (
            select(User)
            .join(GroupMember, GroupMember.user_id == User.id)
            .where(
                and_(
                    User.organization_id == org_id,
                    GroupMember.group_id == group_id,
                )
            )
        )
        return list(self.s.scalars(stmt).all())
