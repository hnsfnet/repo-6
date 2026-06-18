import uuid
from typing import List

from fastapi import HTTPException

from app.models.message import (
    Message, MessageResponse, SendMessageRequest, UnreadCountResponse,
    MessageTargetType
)
from app.services.user_service import user_service
from app.services.group_service import group_service
from app.stores.factory import message_store
from app.channels.channel_manager import channel_manager
from app.core.event_bus import event_bus


class MessageService:
    def __init__(self, store=None, ch_manager=None, bus=None):
        self._store = store or message_store
        self._channel_manager = ch_manager or channel_manager
        self._event_bus = bus or event_bus

    async def send_message(self, request: SendMessageRequest) -> List[MessageResponse]:
        recipient_ids = self._get_recipient_ids(request.target_type, request.target_id)

        if not recipient_ids:
            raise HTTPException(status_code=404, detail="没有找到接收者")

        unique_recipients = list(dict.fromkeys(recipient_ids))
        content_hash = self._store.get_content_hash(request.title, request.content) if hasattr(self._store, 'get_content_hash') else None

        messages = []
        for recipient_id in unique_recipients:
            if content_hash is not None and hasattr(self._store, 'should_send'):
                if not self._store.should_send(recipient_id, content_hash):
                    continue

            message = Message(
                id=str(uuid.uuid4()),
                title=request.title,
                content=request.content,
                priority=request.priority,
                target_type=request.target_type,
                target_id=request.target_id,
                sender_id=request.sender_id
            )
            self._store.save(recipient_id, message)
            if content_hash is not None and hasattr(self._store, 'mark_sent'):
                self._store.mark_sent(recipient_id, content_hash)

            messages.append(message)
            await self._channel_manager.send(
                recipient_id, message,
                target_type=request.target_type.value,
                target_id=request.target_id
            )

            await self._event_bus.publish_event(
                "message.sent",
                message_id=message.id,
                user_id=recipient_id,
                title=message.title
            )

        return [MessageResponse.model_validate(msg) for msg in messages]

    def get_user_messages(self, user_id: str, unread_only: bool = False) -> List[MessageResponse]:
        user = user_service.get_user(user_id)
        if not user:
            raise HTTPException(status_code=404, detail=f"用户 {user_id} 不存在")
        messages = self._store.get_by_user(user_id, unread_only=unread_only)
        return [MessageResponse.model_validate(msg) for msg in messages]

    def get_message_detail(self, user_id: str, message_id: str) -> MessageResponse:
        message = self._store.get(user_id, message_id)
        if not message:
            raise HTTPException(status_code=404, detail=f"消息 {message_id} 不存在")
        return MessageResponse.model_validate(message)

    def mark_as_read(self, user_id: str, message_id: str) -> MessageResponse:
        message = self._store.mark_read(user_id, message_id)
        if not message:
            raise HTTPException(status_code=404, detail=f"消息 {message_id} 不存在")
        return MessageResponse.model_validate(message)

    def mark_all_as_read(self, user_id: str) -> int:
        user = user_service.get_user(user_id)
        if not user:
            raise HTTPException(status_code=404, detail=f"用户 {user_id} 不存在")
        return self._store.mark_all_read(user_id)

    def delete_message(self, user_id: str, message_id: str):
        existing = self._store.get(user_id, message_id)
        if not existing:
            raise HTTPException(status_code=404, detail=f"消息 {message_id} 不存在")
        self._store.delete(user_id, message_id)

    def get_unread_count(self, user_id: str) -> UnreadCountResponse:
        user = user_service.get_user(user_id)
        if not user:
            raise HTTPException(status_code=404, detail=f"用户 {user_id} 不存在")
        return UnreadCountResponse(user_id=user_id, unread_count=self._store.unread_count(user_id))

    def _get_recipient_ids(self, target_type: MessageTargetType, target_id: str) -> List[str]:
        if target_type == MessageTargetType.USER:
            user = user_service.get_user(target_id)
            if not user:
                raise HTTPException(status_code=404, detail=f"用户 {target_id} 不存在")
            return [target_id]
        elif target_type == MessageTargetType.GROUP:
            return group_service.get_group_members(target_id)
        return []


message_service = MessageService()
