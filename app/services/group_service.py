from typing import Dict, List, Optional
from fastapi import HTTPException

from app.models.group import Group, GroupResponse, CreateGroupRequest
from app.services.user_service import user_service
from app.core.config import get_config


class GroupService:
    def __init__(self):
        self._groups: Dict[str, Group] = {}

    def create(self, request: CreateGroupRequest) -> GroupResponse:
        if request.group_id in self._groups:
            raise HTTPException(status_code=400, detail=f"分组 {request.group_id} 已存在")

        group = Group(
            id=request.group_id,
            name=request.name,
            channel=request.channel
        )
        self._groups[request.group_id] = group
        return self._to_response(group)

    def get_group(self, group_id: str) -> Optional[Group]:
        return self._groups.get(group_id)

    def get_group_response(self, group_id: str) -> GroupResponse:
        group = self.get_group(group_id)
        if not group:
            raise HTTPException(status_code=404, detail=f"分组 {group_id} 不存在")
        return self._to_response(group)

    def list_groups(self) -> List[GroupResponse]:
        return [self._to_response(group) for group in self._groups.values()]

    def get_group_channel(self, group_id: str) -> str:
        group = self.get_group(group_id)
        if group and group.channel:
            return group.channel
        cfg = get_config()
        return cfg.group_channels.get(group_id, cfg.default_channel)

    def add_members(self, group_id: str, user_ids: List[str]) -> GroupResponse:
        group = self.get_group(group_id)
        if not group:
            raise HTTPException(status_code=404, detail=f"分组 {group_id} 不存在")

        for user_id in user_ids:
            user = user_service.get_user(user_id)
            if not user:
                raise HTTPException(status_code=404, detail=f"用户 {user_id} 不存在")
            if user_id not in group.members:
                group.members.append(user_id)
                user_service.add_user_to_group(user_id, group_id)

        return self._to_response(group)

    def remove_members(self, group_id: str, user_ids: List[str]) -> GroupResponse:
        group = self.get_group(group_id)
        if not group:
            raise HTTPException(status_code=404, detail=f"分组 {group_id} 不存在")

        for user_id in user_ids:
            if user_id in group.members:
                group.members.remove(user_id)
                user_service.remove_user_from_group(user_id, group_id)

        return self._to_response(group)

    def get_group_members(self, group_id: str) -> List[str]:
        group = self.get_group(group_id)
        if not group:
            raise HTTPException(status_code=404, detail=f"分组 {group_id} 不存在")
        return group.members.copy()

    def _to_response(self, group: Group) -> GroupResponse:
        return GroupResponse(
            id=group.id,
            name=group.name,
            members=group.members.copy(),
            channel=group.channel,
            created_at=group.created_at,
            member_count=len(group.members)
        )


group_service = GroupService()
