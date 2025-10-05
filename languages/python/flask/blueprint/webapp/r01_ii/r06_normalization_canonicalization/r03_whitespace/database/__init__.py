from .storage import DatabaseStorage
from .repository import UserRepository, GroupRepository
from .models import Message, Group

_storage = DatabaseStorage()
user_repository = UserRepository(_storage)
group_repository = GroupRepository(_storage)

# Public API
def authenticate(username: str, password: str) -> bool:
    return user_repository.authenticate(username, password)

def is_group_member(username: str, groupname: str) -> bool:
    return group_repository.is_group_member(username, groupname)

def get_group_messages(groupname: str) -> list[Message]:
    return group_repository.get_group_messages(groupname)

def add_group(group: Group) -> None:
    return group_repository.add_group(group)
