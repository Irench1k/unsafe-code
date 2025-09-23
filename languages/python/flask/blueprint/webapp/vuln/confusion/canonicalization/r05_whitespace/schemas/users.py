from pydantic import BaseModel, ConfigDict, EmailStr

from ..models import User as UserModel


class CreateUser(BaseModel):
    email: EmailStr
    first_name: str
    last_name: str
    password: str
    model_config = ConfigDict(extra='forbid')

class UserDTO(BaseModel):
    email: EmailStr
    first_name: str
    last_name: str
    model_config = ConfigDict(from_attributes=True, frozen=True)

    @classmethod
    def from_db(cls, user: UserModel):
        return cls(email=user.email, first_name=user.first_name, last_name=user.last_name)
