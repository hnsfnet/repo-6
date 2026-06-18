from typing import Dict, List
from app.channels.base_channel import Channel
from app.channels.websocket_channel import WebSocketChannel
from app.models.message import Message
from app.core.config import get_config


class ChannelManager:
    def __init__(self):
        self._channels: Dict[str, Channel] = {}

    def register(self, name: str, channel: Channel):
        self._channels[name] = channel

    def get(self, name: str) -> Channel:
        if name not in self._channels:
            cfg = get_config()
            name = cfg.default_channel
        return self._channels.get(name, self._channels.get(get_config().default_channel))

    def get_for_group(self, group_id: str) -> Channel:
        from app.services.group_service import group_service
        channel_name = group_service.get_group_channel(group_id)
        return self.get(channel_name)

    def get_channels_for_recipient(self, recipient_id: str, target_type: str, target_id: str) -> List[Channel]:
        if target_type == "group":
            return [self.get_for_group(target_id)]
        cfg = get_config()
        return [self.get(cfg.default_channel)]

    async def send(self, user_id: str, message: Message, target_type: str = "user", target_id: str = "") -> bool:
        channels = self.get_channels_for_recipient(user_id, target_type, target_id)
        success = False
        for ch in channels:
            if await ch.send(user_id, message):
                success = True
        return success

    async def broadcast(self, user_ids: List[str], message: Message, target_type: str = "user", target_id: str = "") -> Dict[str, bool]:
        results = {}
        for user_id in user_ids:
            results[user_id] = await self.send(user_id, message, target_type, target_id)
        return results

    def is_online(self, user_id: str) -> bool:
        for ch in self._channels.values():
            if ch.is_online(user_id):
                return True
        return False


channel_manager = ChannelManager()
ws_channel = WebSocketChannel()
channel_manager.register("websocket", ws_channel)
