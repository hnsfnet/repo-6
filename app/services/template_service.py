import re
from datetime import datetime
from typing import Dict, List, Optional
from fastapi import HTTPException

from app.models.template import (
    MessageTemplate, TemplateResponse, CreateTemplateRequest,
    UpdateTemplateRequest, TemplatePreviewRequest, TemplatePreviewResponse
)


class TemplateService:
    def __init__(self):
        self._templates: Dict[str, MessageTemplate] = {}

    def create(self, request: CreateTemplateRequest) -> TemplateResponse:
        if request.template_id in self._templates:
            raise HTTPException(status_code=400, detail=f"模板 {request.template_id} 已存在")

        template = MessageTemplate(
            id=request.template_id,
            title_template=request.title_template,
            content_template=request.content_template,
            description=request.description
        )
        self._templates[request.template_id] = template
        return TemplateResponse.model_validate(template)

    def get(self, template_id: str) -> Optional[MessageTemplate]:
        return self._templates.get(template_id)

    def get_response(self, template_id: str) -> TemplateResponse:
        template = self.get(template_id)
        if not template:
            raise HTTPException(status_code=404, detail=f"模板 {template_id} 不存在")
        return TemplateResponse.model_validate(template)

    def list_all(self) -> List[TemplateResponse]:
        return [TemplateResponse.model_validate(t) for t in self._templates.values()]

    def update(self, template_id: str, request: UpdateTemplateRequest) -> TemplateResponse:
        template = self.get(template_id)
        if not template:
            raise HTTPException(status_code=404, detail=f"模板 {template_id} 不存在")

        if request.title_template is not None:
            template.title_template = request.title_template
        if request.content_template is not None:
            template.content_template = request.content_template
        if request.description is not None:
            template.description = request.description
        template.updated_at = datetime.utcnow()

        return TemplateResponse.model_validate(template)

    def delete(self, template_id: str):
        if template_id not in self._templates:
            raise HTTPException(status_code=404, detail=f"模板 {template_id} 不存在")
        del self._templates[template_id]

    def render(self, template_id: str, params: Dict[str, str]) -> tuple:
        template = self.get(template_id)
        if not template:
            raise HTTPException(status_code=404, detail=f"模板 {template_id} 不存在")

        title = self._replace_placeholders(template.title_template, params)
        content = self._replace_placeholders(template.content_template, params)
        return title, content

    def preview(self, request: TemplatePreviewRequest) -> TemplatePreviewResponse:
        title, content = self.render(request.template_id, request.params)
        return TemplatePreviewResponse(
            template_id=request.template_id,
            title=title,
            content=content,
            params=request.params
        )

    def _replace_placeholders(self, template_str: str, params: Dict[str, str]) -> str:
        def replacer(match):
            key = match.group(1)
            return str(params.get(key, match.group(0)))

        return re.sub(r'\{(\w+)\}', replacer, template_str)


template_service = TemplateService()
