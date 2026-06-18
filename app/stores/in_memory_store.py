import uuid
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from app.stores.base_store import MessageStore
from app.models.message import Message


class InMemoryStore(MessageStore):
    def __init__(self):
        self._all_messages: Dict[str, Message] = {}
        self._user_messages: Dict[str, List[str]] = {}
        self._recent_sent: Dict[Tuple[str, str], datetime] = {}
        self._deduplication_window = timedelta(seconds=60)

    def save(self, user_id: str, message: Message) -> Message:
        if not message.id:
            message.id = str(uuid.uuid4())
        self._all_messages[message.id] = message
        self._add_user_message(user_id, message.id)
        return message

    def get_by_user(self, user_id: str, unread_only: bool = False) -> List[Message]:
        message_ids = self._user_messages.get(user_id, [])
        messages = [self._all_messages[mid] for mid in message_ids if mid in self._all_messages]
        if unread_only:
            messages = [msg for msg in messages if not msg.is_read]
        messages.sort(key=lambda x: x.created_at, reverse=True)
        return messages

    def get(self, user_id: str, message_id: str) -> Optional[Message]:
        message = self._all_messages.get(message_id)
        if not message:
            return None
        user_message_ids = self._user_messages.get(user_id, [])
        if message_id not in user_message_ids:
            return None
        return message

    def mark_read(self, user_id: str, message_id: str) -> Optional[Message]:
        message = self.get(user_id, message_id)
        if not message:
            return None
        message.is_read = True
        message.read_at = datetime.utcnow()
        return message

    def mark_all_read(self, user_id: str) -> int:
        message_ids = self._user_messages.get(user_id, [])
        count = 0
        for mid in message_ids:
            msg = self._all_messages.get(mid)
            if msg and not msg.is_read:
                msg.is_read = True
                msg.read_at = datetime.utcnow()
                count += 1
        return count

    def delete(self, user_id: str, message_id: str):
        user_message_ids = self._user_messages.get(user_id, [])
        if message_id in user_message_ids:
            user_message_ids.remove(message_id)
        if message_id in self._all_messages:
            del self._all_messages[message_id]

    def unread_count(self, user_id: str) -> int:
        message_ids = self._user_messages.get(user_id, [])
        count = 0
        for mid in message_ids:
            msg = self._all_messages.get(mid)
            if msg and not msg.is_read:
                count += 1
        return count

    def _add_user_message(self, user_id: str, message_id: str):
        if user_id not in self._user_messages:
            self._user_messages[user_id] = []
        self._user_messages[user_id].append(message_id)

    def get_content_hash(self, title: str, content: str) -> str:
        combined = f"{title}:{content}"
        return hashlib.md5(combined.encode("utf-8")).hexdigest()

    def should_send(self, user_id: str, content_hash: str) -> bool:
        self._cleanup_expired()
        key = (user_id, content_hash)
        last_sent = self._recent_sent.get(key)
        if last_sent and (datetime.utcnow() - last_sent) < self._deduplication_window:
            return False
        return True

    def mark_sent(self, user_id: str, content_hash: str):
        key = (user_id, content_hash)
        self._recent_sent[key] = datetime.utcnow()

    def _cleanup_expired(self):
        now = datetime.utcnow()
        expired_keys = [
            key for key, last_sent in self._recent_sent.items()
            if (now - last_sent) >= self._deduplication_window
        ]
        for key in expired_keys:
            del self._recent_sent[key]
