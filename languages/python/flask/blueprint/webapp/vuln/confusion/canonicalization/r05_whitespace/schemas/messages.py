from pydantic import BaseModel, ConfigDict, EmailStr
from ..models import Message as MessageModel

# Shared message schema: used for both private and group messages
class Message(BaseModel):
    sender: EmailStr
    message: str
    model_config = ConfigDict(extra='forbid')

    @classmethod
    def from_db(cls, message: MessageModel):
        return cls(sender=message.author.email, message=message.body)

class MessagesDTO(BaseModel):
    recipient: EmailStr
    messages: list[Message]
    model_config = ConfigDict(from_attributes=True, frozen=True)

    @classmethod
    def from_db(cls, recipient: EmailStr, messages: list[Message]):
        return cls(recipient=recipient,
            messages=[Message.from_db(message) for message in messages])
