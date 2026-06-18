from typing import List
from fastapi import APIRouter

from app.models.user import UserResponse, RegisterUserRequest
from app.services.user_service import user_service

router = APIRouter(prefix="/api/users", tags=["用户管理"])


@router.post("/register", response_model=UserResponse, summary="用户注册")
def register_user(request: RegisterUserRequest):
    """
    注册新用户
    - **user_id**: 用户ID
    - **nickname**: 用户昵称
    - **groups**: 所属分组列表
    """
    return user_service.register(request)


@router.get("/{user_id}", response_model=UserResponse, summary="获取用户信息")
def get_user(user_id: str):
    """
    根据用户ID获取用户信息
    """
    return user_service.get_user_response(user_id)


@router.get("", response_model=List[UserResponse], summary="获取所有用户列表")
def list_users():
    """
    获取所有已注册用户列表
    """
    return user_service.list_users()
