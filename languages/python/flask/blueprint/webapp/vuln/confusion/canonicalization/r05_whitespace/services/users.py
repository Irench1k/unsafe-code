import bcrypt

from ..repositories.users import UserRepository
from ..schemas.users import CreateUser, UserDTO


class UserService:
    def __init__(self):
        from flask import g
        self.users = UserRepository(g.db_session)

    def create_user(self, cmd: CreateUser) -> UserDTO:
        user = self.users.create_user(
            cmd.email, cmd.first_name, cmd.last_name,
            bcrypt.hashpw(cmd.password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        )
        return UserDTO.from_db(user)

    def authenticate(self, username: str, password: str) -> bool:
        user = self.users.get_by_username(username)
        if not user:
            return False

        return bcrypt.checkpw(password.encode('utf-8'), user.password_hash.encode('utf-8'))
