from abc import ABC, abstractmethod
from typing import List, Dict

from app.models.message import Message


class Channel(ABC):
    channel_type: str = "base"

    @abstractmethod
    async def send(self, user_id: str, message: Message) -> bool:
        ...

    @abstractmethod
    async def broadcast(self, user_ids: List[str], message: Message) -> Dict[str, bool]:
        ...

    @abstractmethod
    def is_online(self, user_id: str) -> bool:
        ...
