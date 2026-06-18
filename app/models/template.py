from datetime import datetime
from typing import Optional, Dict
from pydantic import BaseModel, Field


class MessageTemplate(BaseModel):
    id: str
    title_template: str
    content_template: str
    description: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None


class CreateTemplateRequest(BaseModel):
    template_id: str
    title_template: str
    content_template: str
    description: Optional[str] = None


class UpdateTemplateRequest(BaseModel):
    title_template: Optional[str] = None
    content_template: Optional[str] = None
    description: Optional[str] = None


class TemplatePreviewRequest(BaseModel):
    template_id: str
    params: Dict[str, str]


class SendTemplateMessageRequest(BaseModel):
    template_id: str
    params: Dict[str, str]
    priority: str = "normal"
    target_type: str
    target_id: str
    sender_id: Optional[str] = None


class TemplateResponse(BaseModel):
    id: str
    title_template: str
    content_template: str
    description: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class TemplatePreviewResponse(BaseModel):
    template_id: str
    title: str
    content: str
    params: Dict[str, str]
