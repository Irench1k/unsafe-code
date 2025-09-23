import bcrypt

from ..db import make_session
from ..repositories.users import UserRepository
from ..schemas.users import CreateUser, UserDTO


class UserService:
    def __init__(self):
        self.s = make_session()
        self.users = UserRepository(self.s)

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
