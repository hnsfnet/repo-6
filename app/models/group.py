from datetime import datetime
from typing import List
from pydantic import BaseModel, Field


class Group(BaseModel):
    id: str
    name: str
    members: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class CreateGroupRequest(BaseModel):
    group_id: str
    name: str


class UpdateGroupMembersRequest(BaseModel):
    user_ids: List[str]


class GroupResponse(BaseModel):
    id: str
    name: str
    members: List[str]
    created_at: datetime
    member_count: int

    class Config:
        from_attributes = True
