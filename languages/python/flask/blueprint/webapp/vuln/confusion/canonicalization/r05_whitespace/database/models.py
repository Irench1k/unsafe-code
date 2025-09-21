from pydantic import BaseModel, constr
from typing import Literal

class Message(BaseModel):
    from_user: str
    message: str

class User(BaseModel):
    name: str
    password: str
    messages: list[Message]

class GroupMember(BaseModel):
    role: Literal["member", "admin"]
    user: str

class Group(BaseModel):
    name: constr(strip_whitespace=True)
    users: list[GroupMember]
    messages: list[Message]
