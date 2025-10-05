from pydantic import BaseModel, StringConstraints
from typing import Literal, Annotated

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

# @unsafe[block]
# id: 4
# part: 2
# @/unsafe
class Group(BaseModel):
    name: Annotated[str, StringConstraints(strip_whitespace=True)]
    users: list[GroupMember]
    messages: list[Message]
# @/unsafe[block]
