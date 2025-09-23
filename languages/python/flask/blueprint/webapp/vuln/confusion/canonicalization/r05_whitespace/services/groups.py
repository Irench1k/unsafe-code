from ..db import make_session
from ..models import RoleEnum
from ..repositories.groups import GroupRepository
from ..repositories.users import UserRepository
from ..schemas.groups import (CreateGroup, CreateGroupMember, GroupDTO,
                              UpdateGroupSettings)


class GroupService:
    def __init__(self):
        self.s = make_session()
        self.groups = GroupRepository(self.s)
        self.users = UserRepository(self.s)

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
