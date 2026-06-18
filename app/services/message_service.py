import uuid
from datetime import datetime
from typing import Dict, List, Optional
from fastapi import HTTPException

from app.models.message import (
    Message, MessageResponse, SendMessageRequest,
    MessagePriority, MessageTargetType, UnreadCountResponse
)
from app.services.user_service import user_service
from app.services.group_service import group_service
from app.services.websocket_manager import websocket_manager


class MessageService:
    def __init__(self):
        self._all_messages: Dict[str, Message] = {}
        self._user_messages: Dict[str, List[str]] = {}

    async def send_message(self, request: SendMessageRequest) -> List[MessageResponse]:
        recipient_ids = self._get_recipient_ids(request.target_type, request.target_id)

        if not recipient_ids:
            raise HTTPException(status_code=404, detail="没有找到接收者")

        messages = []
        for recipient_id in recipient_ids:
            message = Message(
                id=str(uuid.uuid4()),
                title=request.title,
                content=request.content,
                priority=request.priority,
                target_type=request.target_type,
                target_id=request.target_id,
                sender_id=request.sender_id
            )
            self._all_messages[message.id] = message
            self._add_user_message(recipient_id, message.id)
            messages.append(message)
            await websocket_manager.send_message(recipient_id, message)

        return [MessageResponse.model_validate(msg) for msg in messages]

    def get_user_messages(self, user_id: str, unread_only: bool = False) -> List[MessageResponse]:
        user = user_service.get_user(user_id)
        if not user:
            raise HTTPException(status_code=404, detail=f"用户 {user_id} 不存在")

        message_ids = self._user_messages.get(user_id, [])
        messages = [self._all_messages[mid] for mid in message_ids if mid in self._all_messages]

        if unread_only:
            messages = [msg for msg in messages if not msg.is_read]

        messages.sort(key=lambda x: x.created_at, reverse=True)
        return [MessageResponse.model_validate(msg) for msg in messages]

    def get_message_detail(self, user_id: str, message_id: str) -> MessageResponse:
        message = self._all_messages.get(message_id)
        if not message:
            raise HTTPException(status_code=404, detail=f"消息 {message_id} 不存在")

        user_message_ids = self._user_messages.get(user_id, [])
        if message_id not in user_message_ids:
            raise HTTPException(status_code=403, detail="无权访问该消息")

        return MessageResponse.model_validate(message)

    def mark_as_read(self, user_id: str, message_id: str) -> MessageResponse:
        message = self._all_messages.get(message_id)
        if not message:
            raise HTTPException(status_code=404, detail=f"消息 {message_id} 不存在")

        user_message_ids = self._user_messages.get(user_id, [])
        if message_id not in user_message_ids:
            raise HTTPException(status_code=403, detail="无权操作该消息")

        message.is_read = True
        message.read_at = datetime.utcnow()
        return MessageResponse.model_validate(message)

    def mark_all_as_read(self, user_id: str) -> int:
        user = user_service.get_user(user_id)
        if not user:
            raise HTTPException(status_code=404, detail=f"用户 {user_id} 不存在")

        message_ids = self._user_messages.get(user_id, [])
        count = 0
        for mid in message_ids:
            msg = self._all_messages.get(mid)
            if msg and not msg.is_read:
                msg.is_read = True
                msg.read_at = datetime.utcnow()
                count += 1
        return count

    def delete_message(self, user_id: str, message_id: str):
        user_message_ids = self._user_messages.get(user_id, [])
        if message_id not in user_message_ids:
            raise HTTPException(status_code=404, detail=f"消息 {message_id} 不存在")

        user_message_ids.remove(message_id)
        if message_id in self._all_messages:
            del self._all_messages[message_id]

    def get_unread_count(self, user_id: str) -> UnreadCountResponse:
        user = user_service.get_user(user_id)
        if not user:
            raise HTTPException(status_code=404, detail=f"用户 {user_id} 不存在")

        message_ids = self._user_messages.get(user_id, [])
        count = 0
        for mid in message_ids:
            msg = self._all_messages.get(mid)
            if msg and not msg.is_read:
                count += 1

        return UnreadCountResponse(user_id=user_id, unread_count=count)

    def _get_recipient_ids(self, target_type: MessageTargetType, target_id: str) -> List[str]:
        if target_type == MessageTargetType.USER:
            user = user_service.get_user(target_id)
            if not user:
                raise HTTPException(status_code=404, detail=f"用户 {target_id} 不存在")
            return [target_id]
        elif target_type == MessageTargetType.GROUP:
            return group_service.get_group_members(target_id)
        return []

    def _add_user_message(self, user_id: str, message_id: str):
        if user_id not in self._user_messages:
            self._user_messages[user_id] = []
        self._user_messages[user_id].append(message_id)


message_service = MessageService()
