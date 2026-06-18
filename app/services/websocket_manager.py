import json
import asyncio
from typing import Dict, List, Set
from fastapi import WebSocket, WebSocketDisconnect
from datetime import datetime

from app.models.message import Message, MessageResponse
from app.services.user_service import user_service


class WebSocketManager:
    def __init__(self):
        self._active_connections: Dict[str, WebSocket] = {}
        self._heartbeat_tasks: Dict[str, asyncio.Task] = {}
        self._pending_messages: Dict[str, List[Message]] = {}

    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        self._active_connections[user_id] = websocket
        user_service.update_online_status(user_id, True)
        self._start_heartbeat(user_id, websocket)
        await self._send_offline_messages(user_id, websocket)

    async def disconnect(self, user_id: str):
        if user_id in self._active_connections:
            del self._active_connections[user_id]
        if user_id in self._heartbeat_tasks:
            self._heartbeat_tasks[user_id].cancel()
            del self._heartbeat_tasks[user_id]
        user_service.update_online_status(user_id, False)

    def is_online(self, user_id: str) -> bool:
        return user_id in self._active_connections

    async def send_message(self, user_id: str, message: Message):
        if self.is_online(user_id):
            websocket = self._active_connections.get(user_id)
            if not websocket:
                self._add_pending_message(user_id, message)
                return False
            try:
                response = MessageResponse.model_validate(message)
                await websocket.send_text(json.dumps({
                    "type": "message",
                    "data": response.model_dump(mode="json")
                }))
                return True
            except Exception:
                self._add_pending_message(user_id, message)
                await self.disconnect(user_id)
                return False
        else:
            self._add_pending_message(user_id, message)
            return False

    async def broadcast(self, user_ids: List[str], message: Message) -> Dict[str, bool]:
        results = {}
        for user_id in user_ids:
            results[user_id] = await self.send_message(user_id, message)
        return results

    def _start_heartbeat(self, user_id: str, websocket: WebSocket):
        async def heartbeat():
            try:
                while True:
                    await asyncio.sleep(30)
                    await websocket.send_text(json.dumps({
                        "type": "ping",
                        "timestamp": datetime.utcnow().isoformat()
                    }))
            except (WebSocketDisconnect, RuntimeError):
                await self.disconnect(user_id)

        self._heartbeat_tasks[user_id] = asyncio.create_task(heartbeat())

    def _add_pending_message(self, user_id: str, message: Message):
        if user_id not in self._pending_messages:
            self._pending_messages[user_id] = []
        self._pending_messages[user_id].append(message)

    async def _send_offline_messages(self, user_id: str, websocket: WebSocket):
        if user_id in self._pending_messages and self._pending_messages[user_id]:
            pending = self._pending_messages[user_id]
            for message in pending:
                try:
                    response = MessageResponse.model_validate(message)
                    await websocket.send_text(json.dumps({
                        "type": "message",
                        "data": response.model_dump(mode="json")
                    }))
                except Exception:
                    break
            self._pending_messages[user_id] = []

    def get_online_users(self) -> Set[str]:
        return set(self._active_connections.keys())


websocket_manager = WebSocketManager()
