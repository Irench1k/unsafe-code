from ..models import RoleEnum
from ..repositories.groups import GroupRepository
from ..repositories.users import UserRepository
from ..schemas.groups import (CreateGroup, CreateGroupMember, GroupDTO,
                              UpdateGroupSettings)


class GroupService:
    def __init__(self):
        from flask import g
        self.groups = GroupRepository(g.db_session)
        self.users = UserRepository(g.db_session)

    def _same_org(self, owner: str, user: str) -> bool:
        return owner.split('@')[-1] == user.split('@')[-1]

    def create_group(self, owner: str, group: CreateGroup) -> GroupDTO:
        if not self._same_org(owner, group.name):
            raise ValueError("Owner and group must be in the same organization")

        grp = self.groups.create_group(
            name=group.name,
            description=group.description or ""
        )

        # add owner as admin even if they are not in the list
        self.groups.add_member(grp.name, owner, RoleEnum.admin)
        for user in group.users:
            if not self._same_org(owner, user.user):
                # skip users that are not in the same organization
                continue
            if user.user == owner:
                # skip owner, as we already added them as admin
                continue
            else:
                self.groups.add_member(group.name, user.user, user.role)

        return GroupDTO.from_db(grp, self.groups.get_group_members(grp.name))

    def update_group(self, group: str, settings: UpdateGroupSettings) -> GroupDTO:
        grp = self.groups.get_by_name(group)
        if not grp:
            raise ValueError("Group not found")

        for user in settings.users:
            self.groups.add_member(group, user.user, user.role)
        return GroupDTO.from_db(grp, self.groups.get_group_members(grp.name))

    def add_member(self, group: str, member: CreateGroupMember) -> GroupDTO:
        grp = self.groups.get_by_name(group)
        if not grp:
            raise ValueError("Group not found")
        self.groups.add_member(group, member.user, member.role)
        return GroupDTO.from_db(grp, self.groups.get_group_members(grp.name))

    def is_member(self, user_email: str, group_name: str) -> bool:
        """Check if user is member of group"""
        return self.groups.is_user_member(user_email, group_name)

    def is_admin(self, user_email: str, group_name: str) -> bool:
        """Check if user is admin of group"""
        return self.groups.is_user_admin(user_email, group_name)
