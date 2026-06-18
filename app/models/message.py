from enum import Enum
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class MessagePriority(str, Enum):
    NORMAL = "normal"
    IMPORTANT = "important"
    URGENT = "urgent"


class MessageTargetType(str, Enum):
    USER = "user"
    GROUP = "group"


class Message(BaseModel):
    id: str
    title: str
    content: str
    priority: MessagePriority
    target_type: MessageTargetType
    target_id: str
    sender_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    is_read: bool = False
    read_at: Optional[datetime] = None


class SendMessageRequest(BaseModel):
    title: str
    content: str
    priority: MessagePriority = MessagePriority.NORMAL
    target_type: MessageTargetType
    target_id: str
    sender_id: Optional[str] = None


class MessageResponse(BaseModel):
    id: str
    title: str
    content: str
    priority: MessagePriority
    target_type: MessageTargetType
    target_id: str
    sender_id: Optional[str]
    created_at: datetime
    is_read: bool
    read_at: Optional[datetime]

    class Config:
        from_attributes = True


class UnreadCountResponse(BaseModel):
    user_id: str
    unread_count: int
