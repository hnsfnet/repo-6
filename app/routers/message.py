from typing import List
from fastapi import APIRouter, Query

from app.models.message import MessageResponse, SendMessageRequest, UnreadCountResponse
from app.services.message_service import message_service

router = APIRouter(prefix="/api/messages", tags=["消息管理"])


@router.post("/send", response_model=List[MessageResponse], summary="发送消息")
async def send_message(request: SendMessageRequest):
    """
    发送消息给指定用户或分组
    - **title**: 消息标题
    - **content**: 消息内容
    - **priority**: 优先级 (normal/important/urgent)
    - **target_type**: 目标类型 (user/group)
    - **target_id**: 目标ID (用户ID或分组ID)
    - **sender_id**: 发送者ID
    """
    return await message_service.send_message(request)


@router.get("/unread/{user_id}", response_model=List[MessageResponse], summary="获取用户未读消息列表")
def get_unread_messages(user_id: str):
    """
    获取指定用户的未读消息列表，按时间倒序排列
    """
    return message_service.get_user_messages(user_id, unread_only=True)


@router.get("/all/{user_id}", response_model=List[MessageResponse], summary="获取用户所有消息")
def get_all_messages(user_id: str):
    """
    获取指定用户的所有消息列表，按时间倒序排列
    """
    return message_service.get_user_messages(user_id, unread_only=False)


@router.get("/detail/{user_id}/{message_id}", response_model=MessageResponse, summary="获取消息详情")
def get_message_detail(user_id: str, message_id: str):
    """
    获取消息详细内容
    """
    return message_service.get_message_detail(user_id, message_id)


@router.put("/read/{user_id}/{message_id}", response_model=MessageResponse, summary="标记消息已读")
def mark_as_read(user_id: str, message_id: str):
    """
    标记单条消息为已读
    """
    return message_service.mark_as_read(user_id, message_id)


@router.put("/read-all/{user_id}", summary="标记所有消息已读")
def mark_all_as_read(user_id: str):
    """
    标记用户所有未读消息为已读，返回已标记的消息数量
    """
    count = message_service.mark_all_as_read(user_id)
    return {"user_id": user_id, "marked_count": count}


@router.delete("/{user_id}/{message_id}", summary="删除消息")
def delete_message(user_id: str, message_id: str):
    """
    删除指定消息
    """
    message_service.delete_message(user_id, message_id)
    return {"status": "success", "message": "删除成功"}


@router.get("/unread-count/{user_id}", response_model=UnreadCountResponse, summary="获取未读消息数量")
def get_unread_count(user_id: str):
    """
    获取用户未读消息数量
    """
    return message_service.get_unread_count(user_id)
