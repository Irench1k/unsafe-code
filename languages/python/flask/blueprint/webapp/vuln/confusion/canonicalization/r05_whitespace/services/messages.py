from ..repositories.messages import MessageRepository
from ..schemas.messages import MessagesDTO


class MessageService:
    def __init__(self):
        from flask import g
        self.messages = MessageRepository(g.db_session)

    def get_user_messages(self, user: str) -> MessagesDTO:
        messages = self.messages.get_user_messages(user)
        return MessagesDTO.from_db(user, messages)

    def get_group_messages(self, group: str) -> MessagesDTO:
        messages = self.messages.get_group_messages(group)
        return MessagesDTO.from_db(group, messages)
