from sqlalchemy import select, exists, and_
from sqlalchemy.orm import Session
from ..models import Group, GroupMember, RoleEnum


class GroupRepository:
    def __init__(self, session: Session):
        self.s = session

    def get_by_name(self, org_id: int, name: str) -> Group | None:
        stmt = select(Group).where(
            and_(Group.organization_id == org_id, Group.name == name)
        )
        return self.s.scalars(stmt).first()

    def create_group(self, org_id: int, name: str, description: str | None) -> Group:
        grp = Group(organization_id=org_id, name=name, description=description)
        self.s.add(grp)
        self.s.flush()  # get grp.id
        return grp

    def update_group(self, org_id: int, name: str, *, new_name: str | None, description: str | None) -> Group:
        grp = self.get_by_name(org_id, name)
        if not grp:
            raise ValueError("Group not found")
        if new_name:
            grp.name = new_name
        if description is not None:
            grp.description = description
        self.s.flush()
        return grp

    def add_member(self, org_id: int, group_name: str, user_id: int, role: RoleEnum = RoleEnum.member) -> Group:
        grp = self.get_by_name(org_id, group_name)
        if not grp:
            raise ValueError("Group not found")

        # sanity: ensure user belongs to same org
        user = self.s.get(User, user_id)
        if not user or user.organization_id != org_id:
            raise ValueError("User not found in organization")

        link = self.s.get(GroupMember, {"user_id": user_id, "group_id": grp.id})
        if link:
            link.role = role
        else:
            link = GroupMember(user_id=user_id, group_id=grp.id, role=role)
            self.s.add(link)

        self.s.flush()
        return grp

    def is_member(self, user_id: int, group_id: int) -> bool:
        stmt = select(exists().where(
            and_(GroupMember.user_id == user_id, GroupMember.group_id == group_id)
        ))
        return self.s.scalar(stmt)

    def is_admin(self, user_id: int, group_id: int) -> bool:
        stmt = select(exists().where(
            and_(
                GroupMember.user_id == user_id,
                GroupMember.group_id == group_id,
                GroupMember.role == RoleEnum.admin
            )
        ))
        return self.s.scalar(stmt)
