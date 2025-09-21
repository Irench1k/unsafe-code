from .storage import DatabaseStorage
from .repository import UserRepository, GroupRepository
from .models import Message, Group, GroupMember

_storage = DatabaseStorage()
user_repository = UserRepository(_storage)
group_repository = GroupRepository(_storage)

# Public API
def authenticate(username: str, password: str) -> bool:
    return user_repository.authenticate(username, password)

def is_group_member(username: str, groupname: str) -> bool:
    return group_repository.is_group_member(username, groupname)

def is_group_admin(username: str, groupname: str) -> bool:
    return group_repository.is_group_admin(username, groupname)

def get_group_messages(groupname: str) -> list[Message]:
    return group_repository.get_group_messages(groupname)

def add_group(group: Group) -> None:
    return group_repository.add_group(group)

def add_member(groupname: str, member_request: GroupMember) -> None:
    return group_repository.add_member(groupname, member_request)
