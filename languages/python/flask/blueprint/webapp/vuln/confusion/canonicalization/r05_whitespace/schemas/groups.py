from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr

from ..models import Group as GroupModel
from ..models import GroupMember as GroupMemberModel


# Input schemas
class CreateGroupMember(BaseModel):
    role: Literal["member", "admin"]
    user: EmailStr
    model_config = ConfigDict(extra='forbid')

class CreateGroup(BaseModel):
    name: EmailStr
    description: str | None = None
    users: list[CreateGroupMember]
    model_config = ConfigDict(extra='forbid')

class UpdateGroupSettings(BaseModel):
    users: list[CreateGroupMember]
    model_config = ConfigDict(extra='forbid')

# Output schemas
class GroupMemberDTO(BaseModel):
    role: Literal["member", "admin"]
    user: EmailStr
    model_config = ConfigDict(from_attributes=True, frozen=True)

    @classmethod
    def from_db(cls, user: GroupMemberModel):
        return cls(role=user.role.value, user=user.user_email)

class GroupDTO(BaseModel):
    name: EmailStr
    description: str
    users: list[GroupMemberDTO]
    model_config = ConfigDict(from_attributes=True, frozen=True)

    @classmethod
    def from_db(cls, group: GroupModel, users: list[GroupMemberModel]):
        return cls(name=group.name, description=group.description,
            users=[GroupMemberDTO.from_db(user) for user in users])
