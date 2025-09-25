from ..repositories.messages import MessageRepository
from ..repositories.users import UserRepository
from ..schemas.messages import MessagesDTO


class MessageService:
    def __init__(self):
        from flask import g
        self.messages = MessageRepository(g.db_session)
        self.users = UserRepository(g.db_session)

    def get_user_messages(self, user: str) -> MessagesDTO:
        messages = self.messages.get_user_messages(user)
        return MessagesDTO.from_db(user, messages)

    def get_group_messages(self, group: str) -> MessagesDTO:
        messages = self.messages.get_group_messages(group)
        return MessagesDTO.from_db(group, messages)

    def send(self, from_email: str, to_email: str, message: str) -> None:
        # figure out if to_email is a user or a group
        if self.users.get_by_email(to_email):
            self.messages.send_to_user(from_email, to_email, message)
        else:
            self.messages.send_to_group(from_email, to_email, message)
        self.messages.s.commit()
