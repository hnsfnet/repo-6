from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class Group(BaseModel):
    id: str
    name: str
    members: List[str] = Field(default_factory=list)
    channel: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class CreateGroupRequest(BaseModel):
    group_id: str
    name: str
    channel: Optional[str] = None


class UpdateGroupMembersRequest(BaseModel):
    user_ids: List[str]


class GroupResponse(BaseModel):
    id: str
    name: str
    members: List[str]
    channel: Optional[str]
    created_at: datetime
    member_count: int

    class Config:
        from_attributes = True
