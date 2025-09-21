import json
import os

DB_JSON_PATH = "data.json"

class DatabaseStorage:
    def __init__(self):
        relative_path = os.path.join(os.path.dirname(__file__), DB_JSON_PATH)
        self._data = json.load(open(relative_path))

    def get_all_users(self):
        return self._data["users"]

    def get_all_groups(self):
        return self._data["groups"]

    def get_user_by_name(self, username):
        for user in self._data["users"]:
            if user["name"] == username:
                return user
        return None
    
    def get_group_by_name(self, groupname):
        for group in self._data["groups"]:
            if group["name"] == groupname:
                return group
        return None

    def add_group_to_storage(self, new_group):
        new_groups = []        
        for old_group in self._data["groups"]:
            if old_group["name"] == new_group["name"]:
                new_groups.append(new_group)
            else:
                new_groups.append(old_group)

        self._data["groups"] = new_groups
