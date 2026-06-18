import pytest
import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

from app.channels.websocket_channel import WebSocketChannel
from app.models.message import Message, MessagePriority, MessageTargetType
from app.models.user import RegisterUserRequest


@pytest.fixture
def ws_channel():
    return WebSocketChannel()


@pytest.fixture
def test_message():
    return Message(
        id="ws_msg_001",
        title="WS推送消息",
        content="WebSocket实时推送内容",
        priority=MessagePriority.NORMAL,
        target_type=MessageTargetType.USER,
        target_id="ws_user_001"
    )


@pytest.mark.asyncio
async def test_websocket_connect_updates_online_status(ws_channel, user_service):
    user_service.register(RegisterUserRequest(user_id="ws_user_001", nickname="WS用户1", groups=[]))

    mock_ws = MagicMock()
    mock_ws.accept = AsyncMock()
    mock_ws.send_text = AsyncMock()

    await ws_channel.connect(mock_ws, "ws_user_001")

    assert ws_channel.is_online("ws_user_001") is True
    mock_ws.accept.assert_called_once()


@pytest.mark.asyncio
async def test_websocket_disconnect_clears_connection(ws_channel, user_service):
    user_service.register(RegisterUserRequest(user_id="ws_user_002", nickname="WS用户2", groups=[]))

    mock_ws = MagicMock()
    mock_ws.accept = AsyncMock()
    mock_ws.send_text = AsyncMock()

    await ws_channel.connect(mock_ws, "ws_user_002")
    assert ws_channel.is_online("ws_user_002") is True

    await ws_channel.disconnect("ws_user_002")
    assert ws_channel.is_online("ws_user_002") is False


@pytest.mark.asyncio
async def test_online_user_receives_message_in_realtime(ws_channel, user_service):
    user_service.register(RegisterUserRequest(user_id="ws_user_003", nickname="WS用户3", groups=[]))

    mock_ws = MagicMock()
    mock_ws.accept = AsyncMock()
    mock_ws.send_text = AsyncMock()

    await ws_channel.connect(mock_ws, "ws_user_003")

    msg = Message(
        id="rt_001",
        title="实时推送",
        content="在线用户实时收到",
        priority=MessagePriority.NORMAL,
        target_type=MessageTargetType.USER,
        target_id="ws_user_003"
    )
    success = await ws_channel.send("ws_user_003", msg)

    assert success is True
    mock_ws.send_text.assert_called()
    sent_args = mock_ws.send_text.call_args
    sent_data = json.loads(sent_args[0][0])
    assert sent_data["type"] == "message"
    assert sent_data["data"]["title"] == "实时推送"


@pytest.mark.asyncio
async def test_offline_message_saved_to_pending(ws_channel):
    msg = Message(
        id="off_001",
        title="离线消息",
        content="用户不在线时保存",
        priority=MessagePriority.NORMAL,
        target_type=MessageTargetType.USER,
        target_id="ws_user_004"
    )
    success = await ws_channel.send("ws_user_004", msg)

    assert success is False
    assert "ws_user_004" in ws_channel._pending_messages
    assert len(ws_channel._pending_messages["ws_user_004"]) == 1
    assert ws_channel._pending_messages["ws_user_004"][0].title == "离线消息"


@pytest.mark.asyncio
async def test_reconnect_delivers_pending_messages(ws_channel, user_service):
    user_service.register(RegisterUserRequest(user_id="ws_user_005", nickname="WS用户5", groups=[]))

    msg1 = Message(
        id="pend_001",
        title="离线消息1",
        content="待推送1",
        priority=MessagePriority.NORMAL,
        target_type=MessageTargetType.USER,
        target_id="ws_user_005"
    )
    msg2 = Message(
        id="pend_002",
        title="离线消息2",
        content="待推送2",
        priority=MessagePriority.IMPORTANT,
        target_type=MessageTargetType.USER,
        target_id="ws_user_005"
    )
    await ws_channel.send("ws_user_005", msg1)
    await ws_channel.send("ws_user_005", msg2)
    assert len(ws_channel._pending_messages.get("ws_user_005", [])) == 2

    mock_ws = MagicMock()
    mock_ws.accept = AsyncMock()
    mock_ws.send_text = AsyncMock()

    await ws_channel.connect(mock_ws, "ws_user_005")

    assert mock_ws.send_text.call_count >= 2
    sent_titles = []
    for call in mock_ws.send_text.call_args_list:
        data = json.loads(call[0][0])
        if data.get("type") == "message":
            sent_titles.append(data["data"]["title"])

    assert "离线消息1" in sent_titles
    assert "离线消息2" in sent_titles
    assert len(ws_channel._pending_messages.get("ws_user_005", [])) == 0


@pytest.mark.asyncio
async def test_send_failure_triggers_disconnect(ws_channel, user_service):
    user_service.register(RegisterUserRequest(user_id="ws_user_006", nickname="WS用户6", groups=[]))

    mock_ws = MagicMock()
    mock_ws.accept = AsyncMock()
    mock_ws.send_text = AsyncMock(side_effect=Exception("连接已断开"))

    await ws_channel.connect(mock_ws, "ws_user_006")
    assert ws_channel.is_online("ws_user_006") is True

    msg = Message(
        id="fail_001",
        title="发送失败",
        content="测试异常处理",
        priority=MessagePriority.NORMAL,
        target_type=MessageTargetType.USER,
        target_id="ws_user_006"
    )
    success = await ws_channel.send("ws_user_006", msg)

    assert success is False
    assert ws_channel.is_online("ws_user_006") is False
    assert "ws_user_006" in ws_channel._pending_messages


@pytest.mark.asyncio
async def test_broadcast_multiple_users(ws_channel, user_service):
    user_service.register(RegisterUserRequest(user_id="ws_broad_1", nickname="广播1", groups=[]))
    user_service.register(RegisterUserRequest(user_id="ws_broad_2", nickname="广播2", groups=[]))

    mock_ws1 = MagicMock()
    mock_ws1.accept = AsyncMock()
    mock_ws1.send_text = AsyncMock()
    mock_ws2 = MagicMock()
    mock_ws2.accept = AsyncMock()
    mock_ws2.send_text = AsyncMock()

    await ws_channel.connect(mock_ws1, "ws_broad_1")
    await ws_channel.connect(mock_ws2, "ws_broad_2")

    msg = Message(
        id="broad_001",
        title="广播消息",
        content="广播给多个用户",
        priority=MessagePriority.NORMAL,
        target_type=MessageTargetType.GROUP,
        target_id="broad_group"
    )
    results = await ws_channel.broadcast(["ws_broad_1", "ws_broad_2"], msg)

    assert results["ws_broad_1"] is True
    assert results["ws_broad_2"] is True
    assert mock_ws1.send_text.call_count == 1
    assert mock_ws2.send_text.call_count == 1


@pytest.mark.asyncio
async def test_heartbeat_task_created(ws_channel, user_service):
    user_service.register(RegisterUserRequest(user_id="ws_hb", nickname="心跳用户", groups=[]))

    mock_ws = MagicMock()
    mock_ws.accept = AsyncMock()
    mock_ws.send_text = AsyncMock()

    await ws_channel.connect(mock_ws, "ws_hb")

    assert len(ws_channel._heartbeat_tasks) > 0
    assert "ws_hb" in ws_channel._heartbeat_tasks

    ws_channel._heartbeat_tasks["ws_hb"].cancel()
    try:
        await ws_channel._heartbeat_tasks["ws_hb"]
    except asyncio.CancelledError:
        pass
