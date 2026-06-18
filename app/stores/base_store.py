from abc import ABC, abstractmethod
from typing import List, Optional

from app.models.message import Message


class MessageStore(ABC):
    @abstractmethod
    def save(self, user_id: str, message: Message) -> Message:
        ...

    @abstractmethod
    def get_by_user(self, user_id: str, unread_only: bool = False) -> List[Message]:
        ...

    @abstractmethod
    def get(self, user_id: str, message_id: str) -> Optional[Message]:
        ...

    @abstractmethod
    def mark_read(self, user_id: str, message_id: str) -> Optional[Message]:
        ...

    @abstractmethod
    def mark_all_read(self, user_id: str) -> int:
        ...

    @abstractmethod
    def delete(self, user_id: str, message_id: str):
        ...

    @abstractmethod
    def unread_count(self, user_id: str) -> int:
        ...
