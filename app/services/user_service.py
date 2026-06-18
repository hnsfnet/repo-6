from datetime import datetime
from typing import Dict, Optional, List
from fastapi import HTTPException

from app.models.user import User, UserResponse, RegisterUserRequest


class UserService:
    def __init__(self):
        self._users: Dict[str, User] = {}

    def register(self, request: RegisterUserRequest) -> UserResponse:
        if request.user_id in self._users:
            raise HTTPException(status_code=400, detail=f"用户 {request.user_id} 已存在")

        user = User(
            id=request.user_id,
            nickname=request.nickname,
            groups=request.groups.copy()
        )
        self._users[request.user_id] = user
        return UserResponse.model_validate(user)

    def get_user(self, user_id: str) -> Optional[User]:
        return self._users.get(user_id)

    def get_user_response(self, user_id: str) -> UserResponse:
        user = self.get_user(user_id)
        if not user:
            raise HTTPException(status_code=404, detail=f"用户 {user_id} 不存在")
        return UserResponse.model_validate(user)

    def list_users(self) -> List[UserResponse]:
        return [UserResponse.model_validate(user) for user in self._users.values()]

    def update_online_status(self, user_id: str, is_online: bool):
        user = self.get_user(user_id)
        if user:
            user.is_online = is_online
            if is_online:
                user.last_online_at = datetime.utcnow()

    def add_user_to_group(self, user_id: str, group_id: str):
        user = self.get_user(user_id)
        if not user:
            raise HTTPException(status_code=404, detail=f"用户 {user_id} 不存在")
        if group_id not in user.groups:
            user.groups.append(group_id)

    def remove_user_from_group(self, user_id: str, group_id: str):
        user = self.get_user(user_id)
        if user and group_id in user.groups:
            user.groups.remove(group_id)


user_service = UserService()
