from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class User(BaseModel):
    id: str
    nickname: str
    groups: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    is_online: bool = False
    last_online_at: Optional[datetime] = None


class RegisterUserRequest(BaseModel):
    user_id: str
    nickname: str
    groups: List[str] = Field(default_factory=list)


class UserResponse(BaseModel):
    id: str
    nickname: str
    groups: List[str]
    created_at: datetime
    is_online: bool
    last_online_at: Optional[datetime]

    class Config:
        from_attributes = True
