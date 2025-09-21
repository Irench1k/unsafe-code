from .storage import DatabaseStorage
from .models import User, Group, Message, GroupMember

class UserRepository:
    def __init__(self, storage: DatabaseStorage):
        self.storage = storage

    def get_user(self, username: str) -> User:
        """Get the user by name."""
        user_data = self.storage.get_user_by_name(username)
        return User.model_validate(user_data)

    def get_user_messages(self, username: str) -> list[Message]:
        """Get the user's messages."""
        user = self.get_user(username)
        return user.messages

    def authenticate(self, username: str, password: str) -> bool:
        """Authenticate the user."""
        user = self.get_user(username)
        return user.password == password


class GroupRepository:
    def __init__(self, storage: DatabaseStorage):
        self.storage = storage

    def get_group(self, groupname: str) -> Group:
        """Get the group by name."""
        group_data = self.storage.get_group_by_name(groupname)
        return Group.model_validate(group_data)

    def get_group_messages(self, groupname: str) -> list[Message]:
        """Get the group's messages."""
        group = self.get_group(groupname)
        return group.messages

    def is_group_member(self, username: str, groupname: str) -> bool:
        """Check if the user is a member of the group."""
        group = self.get_group(groupname)
        return any((group_member.user == username for group_member in group.users))
    
    def is_group_admin(self, username: str, groupname: str) -> bool:
        """Check if the user is an admin of the group."""
        group = self.get_group(groupname)
        return any((group_member.user == username and group_member.role == "admin" for group_member in group.users))

    def create_group(self, group: Group) -> None:
        """Add a new group to the database."""
        self.storage.add_group_to_storage(group.model_dump())
        
    def update_group(self, group: Group) -> None:
        """Update existing group in the database."""
        self.storage.add_group_to_storage(group.model_dump())
        
    def add_member(self, groupname: str, group_member: GroupMember) -> None:
        """Add a new member to the group."""
        group = self.get_group(groupname)
        
        if self.is_group_member(group_member.user, groupname):
            raise Exception("Member already exists!")
        
        group.users.append(group_member)
        self.update_group(group)
