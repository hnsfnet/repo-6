import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, status

from app.services.websocket_manager import websocket_manager
from app.services.user_service import user_service

router = APIRouter(tags=["WebSocket"])


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    user_id: str = Query(..., description="用户ID")
):
    """
    WebSocket 连接端点
    - 连接时需要携带 user_id 参数
    - 连接成功后会自动推送离线消息
    - 服务端每30秒发送心跳包
    """
    user = user_service.get_user(user_id)
    if not user:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="用户不存在")
        return

    await websocket_manager.connect(websocket, user_id)

    try:
        while True:
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
                if message.get("type") == "pong":
                    continue
            except json.JSONDecodeError:
                pass

    except WebSocketDisconnect:
        await websocket_manager.disconnect(user_id)
    except Exception:
        await websocket_manager.disconnect(user_id)
