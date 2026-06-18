import pytest
import asyncio

from app.models.message import SendMessageRequest, MessagePriority, MessageTargetType, MessageResponse


@pytest.mark.asyncio
async def test_send_single_user_success(message_service, mock_channel, user_service):
    mock_channel.connect("user_001")

    req = SendMessageRequest(
        title="单用户推送",
        content="单用户消息内容",
        priority=MessagePriority.NORMAL,
        target_type=MessageTargetType.USER,
        target_id="user_001"
    )
    results = await message_service.send_message(req)

    assert len(results) == 1
    assert results[0].title == "单用户推送"
    assert results[0].target_id == "user_001"
    assert len(mock_channel.sent_messages) == 1
    assert mock_channel.sent_messages[0]["user_id"] == "user_001"


@pytest.mark.asyncio
async def test_send_group_message(message_service, mock_channel, user_service, group_service):
    mock_channel.connect("user_001")
    mock_channel.connect("user_002")

    req = SendMessageRequest(
        title="分组推送",
        content="分组消息内容",
        priority=MessagePriority.NORMAL,
        target_type=MessageTargetType.GROUP,
        target_id="group_001"
    )
    results = await message_service.send_message(req)

    user_ids = group_service.get_group_members("group_001")
    assert len(results) == len(user_ids)
    titles = {r.title for r in results}
    assert titles == {"分组推送"}


@pytest.mark.asyncio
async def test_group_deduplication_multi_groups(message_service, mock_channel, user_service, group_service):
    mock_channel.connect("user_002")

    req = SendMessageRequest(
        title="跨组去重",
        content="用户2同时在组1和组2，只应收到一次",
        priority=MessagePriority.NORMAL,
        target_type=MessageTargetType.GROUP,
        target_id="group_001"
    )
    results1 = await message_service.send_message(req)

    req2 = SendMessageRequest(
        title="跨组去重",
        content="用户2同时在组1和组2，只应收到一次",
        priority=MessagePriority.NORMAL,
        target_type=MessageTargetType.GROUP,
        target_id="group_002"
    )
    results2 = await message_service.send_message(req2)

    total_sent = sum(1 for m in mock_channel.sent_messages if m["user_id"] == "user_002")
    assert total_sent == 2


@pytest.mark.asyncio
async def test_offline_message_stored(message_service, mock_channel, user_service):
    mock_channel.disconnect("user_001")
    assert not mock_channel.is_online("user_001")

    req = SendMessageRequest(
        title="离线消息",
        content="用户不在线时发送的消息",
        priority=MessagePriority.IMPORTANT,
        target_type=MessageTargetType.USER,
        target_id="user_001"
    )
    results = await message_service.send_message(req)

    assert len(results) == 1
    stored = message_service._store.get_by_user("user_001", unread_only=False)
    assert len(stored) >= 1
    assert any(m.title == "离线消息" for m in stored)


@pytest.mark.asyncio
async def test_message_persisted_in_store(message_service, user_service):
    req = SendMessageRequest(
        title="持久化测试",
        content="消息应该被持久化到存储",
        priority=MessagePriority.NORMAL,
        target_type=MessageTargetType.USER,
        target_id="user_001"
    )
    results = await message_service.send_message(req)
    msg_id = results[0].id

    stored = message_service._store.get("user_001", msg_id)
    assert stored is not None
    assert stored.title == "持久化测试"


def test_get_user_messages(message_service, user_service, message_store):
    from app.models.message import Message
    for i in range(5):
        m = Message(
            id=f"msg_{i}",
            title=f"消息{i}",
            content=f"内容{i}",
            priority=MessagePriority.NORMAL,
            target_type=MessageTargetType.USER,
            target_id="user_001"
        )
        message_store.save("user_001", m)

    msgs = message_service.get_user_messages("user_001", unread_only=False)
    assert len(msgs) == 5


def test_mark_as_read(message_service, user_service, message_store, sample_message):
    message_store.save("user_001", sample_message)
    result = message_service.mark_as_read("user_001", sample_message.id)

    assert result.is_read is True
    assert result.read_at is not None


def test_mark_all_as_read(message_service, user_service, message_store):
    from app.models.message import Message
    for i in range(3):
        m = Message(
            id=f"unread_{i}",
            title=f"未读{i}",
            content=f"未读内容{i}",
            priority=MessagePriority.NORMAL,
            target_type=MessageTargetType.USER,
            target_id="user_001"
        )
        message_store.save("user_001", m)

    count = message_service.mark_all_as_read("user_001")
    assert count >= 3


def test_delete_message(message_service, user_service, message_store, sample_message):
    message_store.save("user_001", sample_message)
    message_service.delete_message("user_001", sample_message.id)

    assert message_store.get("user_001", sample_message.id) is None


def test_get_unread_count(message_service, user_service, message_store):
    from app.models.message import Message
    for i in range(4):
        m = Message(
            id=f"count_{i}",
            title=f"计数{i}",
            content=f"计数内容{i}",
            priority=MessagePriority.NORMAL,
            target_type=MessageTargetType.USER,
            target_id="user_001"
        )
        message_store.save("user_001", m)

    resp = message_service.get_unread_count("user_001")
    assert resp.user_id == "user_001"
    assert resp.unread_count >= 4


def test_message_priority_propagated(message_service, message_store):
    from app.models.message import Message
    for priority in [MessagePriority.NORMAL, MessagePriority.IMPORTANT, MessagePriority.URGENT]:
        m = Message(
            id=f"prio_{priority.value}",
            title=f"优先级测试{priority.value}",
            content="测试",
            priority=priority,
            target_type=MessageTargetType.USER,
            target_id="user_001"
        )
        message_store.save("user_001", m)

    stored = message_store.get_by_user("user_001")
    priorities = {m.priority for m in stored}
    assert MessagePriority.NORMAL in priorities
    assert MessagePriority.IMPORTANT in priorities
    assert MessagePriority.URGENT in priorities
