import os
import sys
import pytest
from unittest.mock import MagicMock, AsyncMock
from typing import List, Dict

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.models.user import User, RegisterUserRequest
from app.models.group import Group, CreateGroupRequest
from app.models.message import Message, SendMessageRequest, MessagePriority, MessageTargetType
from app.models.rule import PushRule
from app.models.template import MessageTemplate
from app.services.user_service import UserService
from app.services.group_service import GroupService
from app.services.message_service import MessageService
from app.services.template_service import TemplateService
from app.services.rule_engine import RuleEngine
from app.stores.in_memory_store import InMemoryStore
from app.channels.base_channel import Channel
from app.channels.channel_manager import ChannelManager
from app.core.event_bus import EventBus, Event
from app.core.config import load_config


@pytest.fixture
def sample_user():
    return User(id="user_001", nickname="测试用户", groups=["group_001"])


@pytest.fixture
def sample_user2():
    return User(id="user_002", nickname="测试用户2", groups=["group_001", "group_002"])


@pytest.fixture
def sample_user3():
    return User(id="user_003", nickname="测试用户3", groups=["group_002"])


@pytest.fixture
def sample_group():
    return Group(id="group_001", name="测试组1", channel="websocket")


@pytest.fixture
def sample_group2():
    return Group(id="group_002", name="测试组2", channel="websocket")


@pytest.fixture
def sample_message():
    return Message(
        id="msg_001",
        title="测试消息",
        content="这是一条测试消息",
        priority=MessagePriority.NORMAL,
        target_type=MessageTargetType.USER,
        target_id="user_001"
    )


@pytest.fixture
def sample_template():
    return MessageTemplate(
        id="tpl_001",
        title_template="订单通知 - {order_id}",
        content_template="用户 {username} 的订单金额为 {amount} 元"
    )


@pytest.fixture
def sample_rule():
    return PushRule(
        id="rule_001",
        name="大额订单通知",
        event_type="order_created",
        condition="amount > 10000",
        template_id="tpl_001",
        target_type="group",
        target_id="group_001",
        priority="important",
        enabled=True
    )


class MockChannel(Channel):
    channel_type = "mock"

    def __init__(self):
        self.sent_messages: List[Dict] = []
        self.online_users: set = set()

    async def send(self, user_id: str, message: Message) -> bool:
        self.sent_messages.append({"user_id": user_id, "message": message})
        return user_id in self.online_users

    async def broadcast(self, user_ids: List[str], message: Message) -> Dict[str, bool]:
        results = {}
        for uid in user_ids:
            results[uid] = await self.send(uid, message)
        return results

    def is_online(self, user_id: str) -> bool:
        return user_id in self.online_users

    def connect(self, user_id: str):
        self.online_users.add(user_id)

    def disconnect(self, user_id: str):
        self.online_users.discard(user_id)


class MockWebSocket:
    def __init__(self):
        self.sent = []
        self.closed = False
        self.accept_called = False

    async def accept(self):
        self.accept_called = True

    async def send_text(self, text: str):
        self.sent.append(text)

    async def close(self, code: int = 1000, reason: str = ""):
        self.closed = True


@pytest.fixture
def mock_channel():
    return MockChannel()


@pytest.fixture
def mock_ws():
    return MockWebSocket()


@pytest.fixture
def user_service():
    svc = UserService()
    svc.register(RegisterUserRequest(user_id="user_001", nickname="用户1", groups=["group_001"]))
    svc.register(RegisterUserRequest(user_id="user_002", nickname="用户2", groups=["group_001", "group_002"]))
    svc.register(RegisterUserRequest(user_id="user_003", nickname="用户3", groups=["group_002"]))
    return svc


@pytest.fixture
def group_service(user_service):
    svc = GroupService()
    svc.create(CreateGroupRequest(group_id="group_001", name="组1"))
    svc.create(CreateGroupRequest(group_id="group_002", name="组2"))
    svc.add_members("group_001", ["user_001", "user_002"])
    svc.add_members("group_002", ["user_002", "user_003"])
    return svc


@pytest.fixture
def message_store():
    return InMemoryStore()


@pytest.fixture
def event_bus():
    return EventBus()


@pytest.fixture
def channel_manager(mock_channel):
    mgr = ChannelManager()
    mgr.register("mock", mock_channel)
    mgr.register("websocket", mock_channel)
    return mgr


@pytest.fixture
def template_service(sample_template):
    svc = TemplateService()
    svc._templates[sample_template.id] = sample_template
    return svc


@pytest.fixture
def message_service(user_service, group_service, message_store, channel_manager, event_bus):
    svc = MessageService(
        store=message_store,
        ch_manager=channel_manager,
        bus=event_bus
    )
    return svc


@pytest.fixture
def rule_engine(template_service, event_bus, sample_rule):
    engine = RuleEngine(bus=event_bus)
    engine._rules[sample_rule.id] = sample_rule
    return engine


@pytest.fixture
def app_client():
    from fastapi.testclient import TestClient
    from app.main import app
    return TestClient(app)
