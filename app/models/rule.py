from datetime import datetime
from typing import Dict, Optional, List
from pydantic import BaseModel, Field


class PushRule(BaseModel):
    id: str
    name: str
    event_type: str
    condition: str
    template_id: str
    target_type: str = "user"
    target_id: str = ""
    priority: str = "normal"
    enabled: bool = True
    description: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class EventReportRequest(BaseModel):
    event_type: str
    event_data: Dict[str, str] = Field(default_factory=dict)
    target_user_id: Optional[str] = None


class PushRuleResponse(BaseModel):
    id: str
    name: str
    event_type: str
    condition: str
    template_id: str
    target_type: str
    target_id: str
    priority: str
    enabled: bool
    description: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class EventReportResponse(BaseModel):
    event_type: str
    matched_rules: List[str]
    messages_sent: int
