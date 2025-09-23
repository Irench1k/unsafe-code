from ..repositories.messages import MessageRepository
from ..schemas.messages import MessagesDTO
from ..db import make_session

class MessageService:
    def __init__(self):
        self.s = make_session()
        self.messages = MessageRepository(self.s)

    def get_user_messages(self, user: str) -> MessagesDTO:
        messages = self.messages.to_user(user)
        return MessagesDTO.from_db(user, messages)

    def get_group_messages(self, group: str) -> MessagesDTO:
        messages = self.messages.to_group(group)
        return MessagesDTO.from_db(group, messages)
