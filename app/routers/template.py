from typing import List
from fastapi import APIRouter

from app.models.template import (
    TemplateResponse, CreateTemplateRequest,
    UpdateTemplateRequest, TemplatePreviewRequest, TemplatePreviewResponse,
    SendTemplateMessageRequest
)
from app.models.message import MessageResponse, MessagePriority, MessageTargetType, SendMessageRequest
from app.services.template_service import template_service
from app.services.message_service import message_service

router = APIRouter(prefix="/api/templates", tags=["消息模板"])


@router.post("", response_model=TemplateResponse, summary="创建消息模板")
def create_template(request: CreateTemplateRequest):
    """
    创建消息模板，模板中可用占位符如 {username}、{order_id} 等
    """
    return template_service.create(request)


@router.get("/{template_id}", response_model=TemplateResponse, summary="获取模板详情")
def get_template(template_id: str):
    """
    根据模板ID获取模板详情
    """
    return template_service.get_response(template_id)


@router.get("", response_model=List[TemplateResponse], summary="获取所有模板列表")
def list_templates():
    """
    获取所有消息模板列表
    """
    return template_service.list_all()


@router.put("/{template_id}", response_model=TemplateResponse, summary="更新模板")
def update_template(template_id: str, request: UpdateTemplateRequest):
    """
    更新模板内容，支持部分更新
    """
    return template_service.update(template_id, request)


@router.delete("/{template_id}", summary="删除模板")
def delete_template(template_id: str):
    """
    删除指定模板
    """
    template_service.delete(template_id)
    return {"status": "success", "message": "模板删除成功"}


@router.post("/preview", response_model=TemplatePreviewResponse, summary="预览模板渲染结果")
def preview_template(request: TemplatePreviewRequest):
    """
    传入模板ID和示例参数，返回渲染后的消息内容，方便调试
    - **template_id**: 模板ID
    - **params**: 占位符参数键值对
    """
    return template_service.preview(request)


@router.post("/send", response_model=List[MessageResponse], summary="使用模板发送消息")
async def send_template_message(request: SendTemplateMessageRequest):
    """
    使用模板发送消息，系统自动替换占位符生成最终内容
    - **template_id**: 模板ID
    - **params**: 占位符参数键值对
    - **priority**: 优先级 (normal/important/urgent)
    - **target_type**: 目标类型 (user/group)
    - **target_id**: 目标ID
    """
    title, content = template_service.render(request.template_id, request.params)

    send_request = SendMessageRequest(
        title=title,
        content=content,
        priority=MessagePriority(request.priority),
        target_type=MessageTargetType(request.target_type),
        target_id=request.target_id,
        sender_id=request.sender_id
    )

    return await message_service.send_message(send_request)
