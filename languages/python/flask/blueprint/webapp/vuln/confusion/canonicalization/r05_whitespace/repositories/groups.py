from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Group, GroupMember, RoleEnum


class GroupRepository:
    def __init__(self, session: Session):
        self.s = session

    def create_group(self, name: str, description: str = "") -> Group:
        """Create a new group"""
        group = Group(name=name, description=description)
        self.s.add(group)
        return group

    def get_by_name(self, name: str) -> Group | None:
        """Get group by name"""
        stmt = select(Group).where(Group.name == name)
        return self.s.scalars(stmt).first()

    def group_exists(self, name: str) -> bool:
        """Check if group exists by name"""
        return self.get_by_name(name) is not None

    def list_groups_for_domain(self, domain: str) -> list[Group]:
        """Get all groups for a domain"""
        stmt = select(Group).where(Group.name.ilike(f'%@{domain}'))
        return list(self.s.scalars(stmt).all())

    def add_member(self, group_name: str, user_email: str, role: RoleEnum):
        """Add member to group using email addresses"""
        # First check if membership already exists
        existing = self.s.scalars(
            select(GroupMember).where(
                (GroupMember.group_name == group_name) &
                (GroupMember.user_email == user_email)
            )
        ).first()

        if existing:
            # Update role if membership exists
            print(f"Existing member {user_email} in group {group_name} with role {existing.role}")
            existing.role = role
        else:
            # Create new membership
            print(f"Creating new member {user_email} in group {group_name} with role {role}")
            member = GroupMember(
                group_name=group_name,
                user_email=user_email,
                role=role
            )
            self.s.add(member)
        print(f"Added member {user_email} to group {group_name} with role {role}")

    def get_group_members(self, group_name: str) -> list[GroupMember]:
        """Get all members of a group by name"""
        stmt = select(GroupMember).where(GroupMember.group_name == group_name)
        return list(self.s.scalars(stmt).all())

    def is_user_member(self, user_email: str, group_name: str) -> bool:
        """Check if user is member of group"""
        stmt = select(GroupMember).where(
            (GroupMember.user_email == user_email) &
            (GroupMember.group_name == group_name)
        )
        return self.s.scalars(stmt).first() is not None

    def is_user_admin(self, user_email: str, group_name: str) -> bool:
        """Check if user is admin of group"""
        stmt = select(GroupMember).where(
            (GroupMember.user_email == user_email) &
            (GroupMember.group_name == group_name) &
            (GroupMember.role == RoleEnum.admin)
        )
        return self.s.scalars(stmt).first() is not None

    def update_group_members(self, group_name: str, members: list[dict]):
        """Update all members of a group - mimicking r04's group update behavior"""
        # Delete existing members
        existing_members = select(GroupMember).where(GroupMember.group_name == group_name)
        for member in self.s.scalars(existing_members):
            self.s.delete(member)

        # Add new members
        for member_data in members:
            self.add_member(
                group_name=group_name,
                user_email=member_data["user"],
                role=RoleEnum(member_data["role"])
            )
