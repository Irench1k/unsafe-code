from ..repositories.users import UserRepository
from ..schemas.users import UserDTO, CreateUser
from ..db import make_session
import bcrypt

class UserService:
    def __init__(self):
        self.s = make_session()
        self.users = UserRepository(self.s)

    def create_user(self, user: CreateUser) -> UserDTO:
        user = self.users.create_user(
            user.email, user.first_name, user.last_name,
            bcrypt.hashpw(user.password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        )
        return UserDTO.from_db(user)

    def authenticate(self, username: str, password: str) -> bool:
        user = self.users.get_by_username(username)
        if not user:
            return False

        return bcrypt.checkpw(password.encode('utf-8'), user.password_hash.encode('utf-8'))
