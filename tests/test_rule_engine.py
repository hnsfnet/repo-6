import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.rule_engine import RuleEngine
from app.models.rule import PushRule, EventReportRequest
from app.models.template import CreateTemplateRequest
from app.core.event_bus import EventBus


@pytest.fixture
def fresh_event_bus():
    return EventBus()


@pytest.fixture
def fresh_rule_engine(fresh_event_bus, template_service):
    return RuleEngine(bus=fresh_event_bus)


@pytest.fixture
def rules_for_conditions():
    return [
        PushRule(
            id="r1",
            name="金额大于10000",
            event_type="order_created",
            condition="amount > 10000",
            template_id="tpl_001",
            target_type="user",
            target_id="user_001",
            priority="normal",
            enabled=True
        ),
        PushRule(
            id="r2",
            name="金额小于等于1000",
            event_type="order_created",
            condition="amount <= 1000",
            template_id="tpl_001",
            target_type="user",
            target_id="user_001",
            priority="normal",
            enabled=True
        ),
        PushRule(
            id="r3",
            name="状态等于已支付",
            event_type="order_created",
            condition='status == "paid"',
            template_id="tpl_001",
            target_type="user",
            target_id="user_001",
            priority="normal",
            enabled=True
        ),
        PushRule(
            id="r4",
            name="包含关键字",
            event_type="comment_created",
            condition='"" in content and "敏感词" in content',
            template_id="tpl_001",
            target_type="user",
            target_id="user_001",
            priority="normal",
            enabled=True
        ),
        PushRule(
            id="r5",
            name="多条件AND",
            event_type="login",
            condition='fail_count >= 3 and location == "异常地区"',
            template_id="tpl_001",
            target_type="user",
            target_id="user_001",
            priority="urgent",
            enabled=True
        ),
        PushRule(
            id="r6",
            name="多条件OR",
            event_type="stock",
            condition="stock < 10 or pending_orders > 100",
            template_id="tpl_001",
            target_type="user",
            target_id="user_001",
            priority="important",
            enabled=True
        ),
    ]


def test_condition_greater_than(fresh_rule_engine, rules_for_conditions):
    engine = fresh_rule_engine
    for r in rules_for_conditions:
        engine._rules[r.id] = r

    matched = engine._match_rules("order_created", {"amount": 15000})
    matched_ids = [m.id for m in matched]
    assert "r1" in matched_ids
    assert "r2" not in matched_ids


def test_condition_less_than_equal(fresh_rule_engine, rules_for_conditions):
    engine = fresh_rule_engine
    for r in rules_for_conditions:
        engine._rules[r.id] = r

    matched = engine._match_rules("order_created", {"amount": 500})
    matched_ids = [m.id for m in matched]
    assert "r2" in matched_ids
    assert "r1" not in matched_ids


def test_condition_equal_string(fresh_rule_engine, rules_for_conditions):
    engine = fresh_rule_engine
    for r in rules_for_conditions:
        engine._rules[r.id] = r

    matched = engine._match_rules("order_created", {"status": "paid"})
    matched_ids = [m.id for m in matched]
    assert "r3" in matched_ids

    matched2 = engine._match_rules("order_created", {"status": "pending"})
    matched_ids2 = [m.id for m in matched2]
    assert "r3" not in matched_ids2


def test_condition_multi_and(fresh_rule_engine, rules_for_conditions):
    engine = fresh_rule_engine
    for r in rules_for_conditions:
        engine._rules[r.id] = r

    matched_both = engine._match_rules("login", {"fail_count": 5, "location": "异常地区"})
    assert "r5" in [m.id for m in matched_both]

    matched_one = engine._match_rules("login", {"fail_count": 5, "location": "北京"})
    assert "r5" not in [m.id for m in matched_one]

    matched_none = engine._match_rules("login", {"fail_count": 1, "location": "北京"})
    assert "r5" not in [m.id for m in matched_none]


def test_condition_multi_or(fresh_rule_engine, rules_for_conditions):
    engine = fresh_rule_engine
    for r in rules_for_conditions:
        engine._rules[r.id] = r

    matched_left = engine._match_rules("stock", {"stock": 5})
    assert "r6" in [m.id for m in matched_left]

    matched_right = engine._match_rules("stock", {"pending_orders": 200, "stock": 100})
    assert "r6" in [m.id for m in matched_right]

    matched_none = engine._match_rules("stock", {"stock": 100, "pending_orders": 50})
    assert "r6" not in [m.id for m in matched_none]


def test_numeric_string_type_conversion(fresh_rule_engine):
    engine = fresh_rule_engine
    engine._rules["num_str"] = PushRule(
        id="num_str",
        name="字符串数字比较",
        event_type="order",
        condition="amount > 10000",
        template_id="tpl_001",
        target_type="user",
        target_id="user_001",
        priority="normal",
        enabled=True
    )

    matched_int = engine._match_rules("order", {"amount": 15000})
    assert len(matched_int) == 1

    matched_str = engine._match_rules("order", {"amount": "15000"})
    assert len(matched_str) == 1

    matched_str_small = engine._match_rules("order", {"amount": "5000"})
    assert len(matched_str_small) == 0


def test_numeric_string_with_currency_and_comma(fresh_rule_engine):
    engine = fresh_rule_engine
    engine._rules["r_currency"] = PushRule(
        id="r_currency",
        name="人民币比较",
        event_type="order",
        condition="amount > 10000",
        template_id="tpl_001",
        target_type="user",
        target_id="user_001",
        priority="normal",
        enabled=True
    )

    matched_rmb = engine._match_rules("order", {"amount": "¥15,000"})
    assert len(matched_rmb) == 1, "¥15,000 应被解析为 15000，触发规则"

    not_matched = engine._match_rules("order", {"amount": "¥5,000"})
    assert len(not_matched) == 0, "¥5,000 应被解析为 5000，不触发规则"


def test_string_comparison_preserved_when_not_numeric(fresh_rule_engine):
    engine = fresh_rule_engine
    engine._rules["r_str_cmp"] = PushRule(
        id="r_str_cmp",
        name="纯字符串比较",
        event_type="user_event",
        condition='role == "admin"',
        template_id="tpl_001",
        target_type="user",
        target_id="user_001",
        priority="normal",
        enabled=True
    )

    matched = engine._match_rules("user_event", {"role": "admin"})
    assert len(matched) == 1

    not_matched = engine._match_rules("user_event", {"role": "user"})
    assert len(not_matched) == 0


def test_multiple_rules_sorted_by_priority(fresh_rule_engine):
    engine = fresh_rule_engine
    engine._rules["p_low"] = PushRule(
        id="p_low", name="低优先级", event_type="x", condition="1 == 1",
        template_id="tpl_001", target_type="user", target_id="u1",
        priority="normal", enabled=True
    )
    engine._rules["p_mid"] = PushRule(
        id="p_mid", name="中优先级", event_type="x", condition="1 == 1",
        template_id="tpl_001", target_type="user", target_id="u1",
        priority="important", enabled=True
    )
    engine._rules["p_high"] = PushRule(
        id="p_high", name="高优先级", event_type="x", condition="1 == 1",
        template_id="tpl_001", target_type="user", target_id="u1",
        priority="urgent", enabled=True
    )

    matched = engine._match_rules("x", {})
    order = [m.priority for m in matched]

    assert order == ["urgent", "important", "normal"]


def test_disabled_rules_not_matched(fresh_rule_engine):
    engine = fresh_rule_engine
    engine._rules["disabled"] = PushRule(
        id="disabled", name="已禁用", event_type="event", condition="1 == 1",
        template_id="tpl_001", target_type="user", target_id="u1",
        priority="normal", enabled=False
    )
    engine._rules["enabled"] = PushRule(
        id="enabled", name="已启用", event_type="event", condition="1 == 1",
        template_id="tpl_001", target_type="user", target_id="u1",
        priority="normal", enabled=True
    )

    matched = engine._match_rules("event", {})
    matched_ids = [m.id for m in matched]
    assert "enabled" in matched_ids
    assert "disabled" not in matched_ids


def test_event_type_mismatch(fresh_rule_engine):
    engine = fresh_rule_engine
    engine._rules["r"] = PushRule(
        id="r", name="类型A", event_type="type_a", condition="1 == 1",
        template_id="tpl_001", target_type="user", target_id="u1",
        priority="normal", enabled=True
    )

    matched_a = engine._match_rules("type_a", {})
    assert len(matched_a) == 1

    matched_b = engine._match_rules("type_b", {})
    assert len(matched_b) == 0


@pytest.mark.asyncio
async def test_process_event_triggers_message_push(fresh_rule_engine, template_service):
    engine = fresh_rule_engine
    engine._rules["r1"] = PushRule(
        id="r1",
        name="测试推送",
        event_type="test_event",
        condition='value == "trigger"',
        template_id="tpl_001",
        target_type="user",
        target_id="user_001",
        priority="important",
        enabled=True
    )

    with patch.object(engine, "_send_push_notification", new_callable=AsyncMock) as mock_send:
        req = EventReportRequest(
            event_type="test_event",
            event_data={"value": "trigger", "username": "张三", "order_id": "O001", "amount": 100}
        )
        results = await engine.process_event(req)

        assert len(results) == 1
        assert mock_send.call_count == 1
        args, kwargs = mock_send.call_args
        matched_rule = args[0]
        params = args[1]
        assert matched_rule.id == "r1"
        assert params["username"] == "张三"


@pytest.mark.asyncio
async def test_event_bus_subscription_publishes_push_event(fresh_rule_engine, fresh_event_bus):
    engine = fresh_rule_engine
    engine._rules["eb_test"] = PushRule(
        id="eb_test",
        name="事件总线测试",
        event_type="eb_trigger",
        condition='data == "ok"',
        template_id="tpl_001",
        target_type="user",
        target_id="user_001",
        priority="normal",
        enabled=True
    )

    push_events = []

    async def capture_push(event):
        push_events.append(event)

    fresh_event_bus.subscribe("push.triggered", capture_push)

    await fresh_event_bus.publish_event(
        "event.reported",
        event_type="eb_trigger",
        event_data={"data": "ok", "username": "李四", "order_id": "O002", "amount": 50}
    )
    await asyncio.sleep(0.05)

    assert len(push_events) >= 1
    pe = push_events[0]
    assert pe.data["rule_id"] == "eb_test"


def test_parse_numeric_value_float():
    from app.services.rule_engine import RuleEngine
    engine = RuleEngine()

    assert engine._parse_numeric_value("123.45") == 123.45
    assert engine._parse_numeric_value("123") == 123
    assert engine._parse_numeric_value("abc") == "abc"
    assert engine._parse_numeric_value("¥999.99") == 999.99


def test_load_from_yaml(tmp_path):
    from app.services.rule_engine import RuleEngine
    yaml_content = """
rules:
  - id: yaml_r1
    name: YAML加载测试
    event_type: yaml_event
    condition: "count > 5"
    template_id: tpl_yaml
    target_type: user
    target_id: u_yaml
    priority: important
    enabled: true
    description: "测试描述"
"""
    yaml_file = tmp_path / "test_rules.yaml"
    yaml_file.write_text(yaml_content, encoding="utf-8")

    engine = RuleEngine()
    engine.load_from_yaml(str(yaml_file))

    assert "yaml_r1" in engine._rules
    rule = engine._rules["yaml_r1"]
    assert rule.name == "YAML加载测试"
    assert rule.event_type == "yaml_event"
    assert rule.priority == "important"
