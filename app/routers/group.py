from typing import List
from fastapi import APIRouter

from app.models.group import GroupResponse, CreateGroupRequest, UpdateGroupMembersRequest
from app.services.group_service import group_service

router = APIRouter(prefix="/api/groups", tags=["分组管理"])


@router.post("", response_model=GroupResponse, summary="创建分组")
def create_group(request: CreateGroupRequest):
    """
    创建新分组
    - **group_id**: 分组ID
    - **name**: 分组名称
    """
    return group_service.create(request)


@router.get("/{group_id}", response_model=GroupResponse, summary="获取分组信息")
def get_group(group_id: str):
    """
    根据分组ID获取分组信息
    """
    return group_service.get_group_response(group_id)


@router.get("", response_model=List[GroupResponse], summary="获取所有分组列表")
def list_groups():
    """
    获取所有分组列表
    """
    return group_service.list_groups()


@router.post("/{group_id}/members", response_model=GroupResponse, summary="添加成员")
def add_members(group_id: str, request: UpdateGroupMembersRequest):
    """
    向分组添加成员
    - **group_id**: 分组ID
    - **user_ids**: 用户ID列表
    """
    return group_service.add_members(group_id, request.user_ids)


@router.delete("/{group_id}/members", response_model=GroupResponse, summary="移除成员")
def remove_members(group_id: str, request: UpdateGroupMembersRequest):
    """
    从分组移除成员
    - **group_id**: 分组ID
    - **user_ids**: 用户ID列表
    """
    return group_service.remove_members(group_id, request.user_ids)
