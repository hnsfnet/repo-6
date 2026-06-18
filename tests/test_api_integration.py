import pytest
import json
from unittest.mock import patch


def test_health_endpoint(app_client):
    resp = app_client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert "信达" in body["service"]


def test_root_endpoint(app_client):
    resp = app_client.get("/")
    assert resp.status_code == 200
    body = resp.json()
    assert body["docs"] == "/docs"


class TestUserAPI:

    def test_register_user_success(self, app_client):
        resp = app_client.post(
            "/api/users/register",
            json={"user_id": "test_user_1", "nickname": "测试用户1", "groups": []}
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["id"] == "test_user_1"
        assert body["nickname"] == "测试用户1"

    def test_register_duplicate_user(self, app_client):
        app_client.post(
            "/api/users/register",
            json={"user_id": "dup_user", "nickname": "重复", "groups": []}
        )
        resp = app_client.post(
            "/api/users/register",
            json={"user_id": "dup_user", "nickname": "重复2", "groups": []}
        )
        assert resp.status_code == 400

    def test_get_user_success(self, app_client):
        app_client.post(
            "/api/users/register",
            json={"user_id": "get_user_1", "nickname": "查询用户", "groups": ["g1"]}
        )
        resp = app_client.get("/api/users/get_user_1")
        assert resp.status_code == 200
        body = resp.json()
        assert body["id"] == "get_user_1"
        assert body["nickname"] == "查询用户"
        assert body["groups"] == ["g1"]

    def test_get_user_not_found(self, app_client):
        resp = app_client.get("/api/users/nonexistent_user")
        assert resp.status_code == 404

    def test_list_users(self, app_client):
        app_client.post(
            "/api/users/register",
            json={"user_id": "list_u1", "nickname": "列表用户1", "groups": []}
        )
        app_client.post(
            "/api/users/register",
            json={"user_id": "list_u2", "nickname": "列表用户2", "groups": []}
        )
        resp = app_client.get("/api/users")
        assert resp.status_code == 200
        body = resp.json()
        assert isinstance(body, list)
        ids = [u["id"] for u in body]
        assert "list_u1" in ids
        assert "list_u2" in ids


class TestGroupAPI:

    def test_create_group_success(self, app_client):
        resp = app_client.post(
            "/api/groups/create",
            json={"group_id": "test_group_1", "name": "测试组1", "channel": "websocket"}
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["id"] == "test_group_1"
        assert body["name"] == "测试组1"
        assert body["channel"] == "websocket"

    def test_create_group_default_channel(self, app_client):
        resp = app_client.post(
            "/api/groups/create",
            json={"group_id": "test_group_2", "name": "测试组2"}
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["id"] == "test_group_2"

    def test_get_group_success(self, app_client):
        app_client.post(
            "/api/groups/create",
            json={"group_id": "get_g1", "name": "查询组"}
        )
        resp = app_client.get("/api/groups/get_g1")
        assert resp.status_code == 200
        body = resp.json()
        assert body["id"] == "get_g1"
        assert body["name"] == "查询组"

    def test_get_group_not_found(self, app_client):
        resp = app_client.get("/api/groups/nonexistent_group")
        assert resp.status_code == 404

    def test_add_members(self, app_client):
        app_client.post(
            "/api/users/register",
            json={"user_id": "gm_1", "nickname": "组成员1", "groups": []}
        )
        app_client.post(
            "/api/users/register",
            json={"user_id": "gm_2", "nickname": "组成员2", "groups": []}
        )
        app_client.post(
            "/api/groups/create",
            json={"group_id": "mem_g1", "name": "成员组", "channel": "websocket"}
        )
        resp = app_client.post(
            "/api/groups/mem_g1/members/add",
            json={"user_ids": ["gm_1", "gm_2"]}
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "gm_1" in body["members"]
        assert "gm_2" in body["members"]

    def test_remove_members(self, app_client):
        app_client.post(
            "/api/users/register",
            json={"user_id": "rm_1", "nickname": "移除成员1", "groups": []}
        )
        app_client.post(
            "/api/groups/create",
            json={"group_id": "rm_g1", "name": "移除组", "channel": "websocket"}
        )
        app_client.post(
            "/api/groups/rm_g1/members/add",
            json={"user_ids": ["rm_1"]}
        )
        resp = app_client.post(
            "/api/groups/rm_g1/members/remove",
            json={"user_ids": ["rm_1"]}
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "rm_1" not in body["members"]


class TestMessageAPI:

    def test_send_message_single_user(self, app_client):
        app_client.post(
            "/api/users/register",
            json={"user_id": "msg_u1", "nickname": "消息用户1", "groups": []}
        )
        resp = app_client.post(
            "/api/messages/send",
            json={
                "title": "API测试消息",
                "content": "单用户消息内容",
                "priority": "normal",
                "target_type": "user",
                "target_id": "msg_u1"
            }
        )
        assert resp.status_code == 200
        body = resp.json()
        assert isinstance(body, list)
        assert len(body) >= 1
        assert body[0]["title"] == "API测试消息"

    def test_send_message_invalid_user(self, app_client):
        resp = app_client.post(
            "/api/messages/send",
            json={
                "title": "发给不存在的用户",
                "content": "内容",
                "priority": "normal",
                "target_type": "user",
                "target_id": "invalid_user_id_12345"
            }
        )
        assert resp.status_code == 404

    def test_send_message_invalid_group(self, app_client):
        resp = app_client.post(
            "/api/messages/send",
            json={
                "title": "发给不存在的分组",
                "content": "内容",
                "priority": "normal",
                "target_type": "group",
                "target_id": "invalid_group_id_12345"
            }
        )
        assert resp.status_code == 404

    def test_get_unread_messages(self, app_client):
        app_client.post(
            "/api/users/register",
            json={"user_id": "unread_u1", "nickname": "未读用户", "groups": []}
        )
        app_client.post(
            "/api/messages/send",
            json={
                "title": "未读消息1",
                "content": "c1",
                "priority": "normal",
                "target_type": "user",
                "target_id": "unread_u1"
            }
        )
        app_client.post(
            "/api/messages/send",
            json={
                "title": "未读消息2",
                "content": "c2",
                "priority": "normal",
                "target_type": "user",
                "target_id": "unread_u1"
            }
        )
        resp = app_client.get("/api/messages/unread?user_id=unread_u1")
        assert resp.status_code == 200
        body = resp.json()
        titles = [m["title"] for m in body]
        assert "未读消息1" in titles
        assert "未读消息2" in titles
        assert all(m["is_read"] is False for m in body)

    def test_mark_as_read(self, app_client):
        app_client.post(
            "/api/users/register",
            json={"user_id": "read_u1", "nickname": "已读用户", "groups": []}
        )
        s_resp = app_client.post(
            "/api/messages/send",
            json={
                "title": "标记已读",
                "content": "内容",
                "priority": "normal",
                "target_type": "user",
                "target_id": "read_u1"
            }
        )
        msg_id = s_resp.json()[0]["id"]
        resp = app_client.post(f"/api/messages/{msg_id}/read?user_id=read_u1")
        assert resp.status_code == 200
        body = resp.json()
        assert body["is_read"] is True
        assert body["read_at"] is not None

    def test_mark_all_as_read(self, app_client):
        app_client.post(
            "/api/users/register",
            json={"user_id": "allread_u1", "nickname": "全部已读", "groups": []}
        )
        for i in range(3):
            app_client.post(
                "/api/messages/send",
                json={
                    "title": f"全读{i}",
                    "content": "c",
                    "priority": "normal",
                    "target_type": "user",
                    "target_id": "allread_u1"
                }
            )
        resp = app_client.post("/api/messages/read-all?user_id=allread_u1")
        assert resp.status_code == 200
        body = resp.json()
        assert body["marked_count"] >= 3

    def test_get_unread_count(self, app_client):
        app_client.post(
            "/api/users/register",
            json={"user_id": "count_u1", "nickname": "计数用户", "groups": []}
        )
        for i in range(4):
            app_client.post(
                "/api/messages/send",
                json={
                    "title": f"计数{i}",
                    "content": "c",
                    "priority": "normal",
                    "target_type": "user",
                    "target_id": "count_u1"
                }
            )
        resp = app_client.get("/api/messages/unread-count?user_id=count_u1")
        assert resp.status_code == 200
        body = resp.json()
        assert body["user_id"] == "count_u1"
        assert body["unread_count"] >= 4

    def test_delete_message(self, app_client):
        app_client.post(
            "/api/users/register",
            json={"user_id": "del_u1", "nickname": "删除用户", "groups": []}
        )
        s_resp = app_client.post(
            "/api/messages/send",
            json={
                "title": "待删除",
                "content": "内容",
                "priority": "normal",
                "target_type": "user",
                "target_id": "del_u1"
            }
        )
        msg_id = s_resp.json()[0]["id"]
        resp = app_client.delete(f"/api/messages/{msg_id}?user_id=del_u1")
        assert resp.status_code == 200
        assert resp.json()["success"] is True

        detail_resp = app_client.get(f"/api/messages/{msg_id}?user_id=del_u1")
        assert detail_resp.status_code == 404


class TestTemplateAPI:

    def test_create_template(self, app_client):
        resp = app_client.post(
            "/api/templates/create",
            json={
                "title_template": "订单通知-{order_id}",
                "content_template": "用户{username}下单，金额{amount}元"
            }
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["id"] is not None
        assert "{order_id}" in body["title_template"]

    def test_get_template(self, app_client):
        c_resp = app_client.post(
            "/api/templates/create",
            json={
                "title_template": "查询模板",
                "content_template": "模板内容{var}"
            }
        )
        tpl_id = c_resp.json()["id"]
        resp = app_client.get(f"/api/templates/{tpl_id}")
        assert resp.status_code == 200
        assert resp.json()["title_template"] == "查询模板"

    def test_get_template_not_found(self, app_client):
        resp = app_client.get("/api/templates/nonexistent_template_12345")
        assert resp.status_code == 404

    def test_list_templates(self, app_client):
        app_client.post(
            "/api/templates/create",
            json={"title_template": "列表模板A", "content_template": "A"}
        )
        app_client.post(
            "/api/templates/create",
            json={"title_template": "列表模板B", "content_template": "B"}
        )
        resp = app_client.get("/api/templates")
        assert resp.status_code == 200
        body = resp.json()
        assert isinstance(body, list)
        assert len(body) >= 2

    def test_update_template(self, app_client):
        c_resp = app_client.post(
            "/api/templates/create",
            json={"title_template": "旧标题", "content_template": "旧内容"}
        )
        tpl_id = c_resp.json()["id"]
        resp = app_client.put(
            f"/api/templates/{tpl_id}",
            json={"title_template": "新标题", "content_template": "新内容"}
        )
        assert resp.status_code == 200
        assert resp.json()["title_template"] == "新标题"

    def test_delete_template(self, app_client):
        c_resp = app_client.post(
            "/api/templates/create",
            json={"title_template": "待删", "content_template": "待删"}
        )
        tpl_id = c_resp.json()["id"]
        resp = app_client.delete(f"/api/templates/{tpl_id}")
        assert resp.status_code == 200
        assert resp.json()["success"] is True

    def test_preview_template(self, app_client):
        c_resp = app_client.post(
            "/api/templates/create",
            json={
                "title_template": "订单{order_id}",
                "content_template": "金额{amount}元"
            }
        )
        tpl_id = c_resp.json()["id"]
        resp = app_client.post(
            "/api/templates/preview",
            json={"template_id": tpl_id, "params": {"order_id": "O001", "amount": "999"}}
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["title"] == "订单O001"
        assert body["content"] == "金额999元"

    def test_send_template_message(self, app_client):
        app_client.post(
            "/api/users/register",
            json={"user_id": "tpl_user", "nickname": "模板用户", "groups": []}
        )
        c_resp = app_client.post(
            "/api/templates/create",
            json={
                "title_template": "模板标题",
                "content_template": "用户{username}"
            }
        )
        tpl_id = c_resp.json()["id"]
        resp = app_client.post(
            "/api/templates/send",
            json={
                "template_id": tpl_id,
                "params": {"username": "张三"},
                "priority": "normal",
                "target_type": "user",
                "target_id": "tpl_user"
            }
        )
        assert resp.status_code == 200
        body = resp.json()
        assert isinstance(body, list)
        assert body[0]["title"] == "模板标题"
        assert body[0]["content"] == "用户张三"

    def test_send_template_not_found(self, app_client):
        resp = app_client.post(
            "/api/templates/send",
            json={
                "template_id": "nonexistent_tpl_12345",
                "params": {},
                "priority": "normal",
                "target_type": "user",
                "target_id": "any"
            }
        )
        assert resp.status_code == 404


class TestEventAndRuleAPI:

    def test_list_rules(self, app_client):
        resp = app_client.get("/api/events/rules")
        assert resp.status_code == 200
        body = resp.json()
        assert isinstance(body, list)

    def test_get_rule_not_found(self, app_client):
        resp = app_client.get("/api/events/rules/nonexistent_rule")
        assert resp.status_code == 404

    def test_toggle_rule(self, app_client):
        from app.services.rule_engine import rule_engine
        from app.models.rule import PushRule
        rule_engine._rules["toggle_r1"] = PushRule(
            id="toggle_r1", name="切换测试", event_type="t", condition="1==1",
            template_id="tpl", target_type="user", target_id="u",
            priority="normal", enabled=True
        )
        resp = app_client.post("/api/events/rules/toggle_r1/toggle")
        assert resp.status_code == 200
        assert resp.json()["enabled"] is False

        resp2 = app_client.post("/api/events/rules/toggle_r1/toggle")
        assert resp2.json()["enabled"] is True

    def test_report_event_triggers_rule(self, app_client):
        from app.services.rule_engine import rule_engine
        from app.services.template_service import template_service
        from app.services.user_service import user_service
        from app.services.group_service import group_service
        from app.models.rule import PushRule
        from app.models.user import RegisterUserRequest
        from app.models.group import CreateGroupRequest
        from app.models.template import MessageTemplate

        user_service.register(RegisterUserRequest(user_id="evt_user", nickname="事件用户", groups=[]))
        group_service.create(CreateGroupRequest(group_id="evt_group", name="事件组", channel="websocket"))
        group_service.add_members("evt_group", ["evt_user"])
        template_service._templates["evt_tpl"] = MessageTemplate(
            id="evt_tpl",
            title_template="大额订单-{order_id}",
            content_template="金额{amount}元"
        )
        rule_engine._rules["evt_r1"] = PushRule(
            id="evt_r1",
            name="测试事件",
            event_type="evt_order",
            condition="amount > 10000",
            template_id="evt_tpl",
            target_type="group",
            target_id="evt_group",
            priority="important",
            enabled=True
        )

        resp = app_client.post(
            "/api/events/report",
            json={
                "event_type": "evt_order",
                "event_data": {
                    "amount": 50000,
                    "order_id": "EVT001",
                    "username": "李四"
                }
            }
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["event_type"] == "evt_order"
        assert body["matched_rules_count"] >= 1

        msgs_resp = app_client.get("/api/messages/unread?user_id=evt_user")
        assert msgs_resp.status_code == 200
        msgs = msgs_resp.json()
        titles = [m["title"] for m in msgs]
        assert any("大额订单" in t for t in titles)


class TestWebSocketAPI:

    def test_websocket_connect_requires_user_id(self, app_client):
        with app_client.websocket_connect("/ws") as ws:
            ws.send_json({"type": "ping"})
            data = ws.receive_json()
            assert data["type"] == "error"

    def test_websocket_connect_success(self, app_client):
        app_client.post(
            "/api/users/register",
            json={"user_id": "ws_test_1", "nickname": "WS测试", "groups": []}
        )
        with app_client.websocket_connect("/ws?user_id=ws_test_1") as ws:
            ws.send_json({"type": "ping"})
            data = ws.receive_json()
            assert data["type"] == "connected"
            assert data["user_id"] == "ws_test_1"
