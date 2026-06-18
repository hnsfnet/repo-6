import os
import re
import logging
from typing import Dict, List, Optional
import yaml
from fastapi import HTTPException

from app.models.rule import PushRule, PushRuleResponse, EventReportRequest, EventReportResponse
from app.models.message import SendMessageRequest, MessagePriority, MessageTargetType
from app.services.template_service import template_service
from app.core.event_bus import Event, event_bus

logger = logging.getLogger(__name__)


class RuleEngine:
    def __init__(self, bus=None):
        self._rules: Dict[str, PushRule] = {}
        self._event_bus = bus or event_bus
        self._setup_subscribers()

    def _setup_subscribers(self):
        self._event_bus.subscribe("event.reported", self._on_event_reported)

    async def _on_event_reported(self, event: Event):
        req = EventReportRequest(**event.data)
        await self.process_event(req)

    def load_from_yaml(self, yaml_path: str):
        if not os.path.exists(yaml_path):
            logger.warning(f"规则配置文件 {yaml_path} 不存在，跳过加载")
            return

        with open(yaml_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        if not data or "rules" not in data:
            logger.warning("规则配置文件格式无效，未找到 rules 字段")
            return

        for rule_data in data["rules"]:
            rule = PushRule(**rule_data)
            self._rules[rule.id] = rule
            logger.info(f"已加载规则: {rule.id} - {rule.name}")

    def get_rule(self, rule_id: str) -> Optional[PushRule]:
        return self._rules.get(rule_id)

    def get_rule_response(self, rule_id: str) -> PushRuleResponse:
        rule = self.get_rule(rule_id)
        if not rule:
            raise HTTPException(status_code=404, detail=f"规则 {rule_id} 不存在")
        return PushRuleResponse.model_validate(rule)

    def list_rules(self) -> List[PushRuleResponse]:
        return [PushRuleResponse.model_validate(r) for r in self._rules.values()]

    def toggle_rule(self, rule_id: str, enabled: bool) -> PushRuleResponse:
        rule = self.get_rule(rule_id)
        if not rule:
            raise HTTPException(status_code=404, detail=f"规则 {rule_id} 不存在")
        rule.enabled = enabled
        return PushRuleResponse.model_validate(rule)

    async def process_event(self, request: EventReportRequest) -> EventReportResponse:
        matched_rules = []
        messages_sent = 0

        for rule in self._rules.values():
            if not rule.enabled:
                continue
            if rule.event_type != request.event_type:
                continue
            if not self._evaluate_condition(rule.condition, request.event_data):
                continue

            matched_rules.append(rule.id)

            try:
                title, content = template_service.render(rule.template_id, request.event_data)
            except HTTPException:
                logger.warning(f"规则 {rule.id} 引用的模板 {rule.template_id} 不存在，跳过")
                continue

            target_type = MessageTargetType(rule.target_type)
            target_id = rule.target_id

            if target_type == MessageTargetType.USER and request.target_user_id:
                target_id = request.target_user_id

            priority = MessagePriority(rule.priority)

            await self._event_bus.publish_event(
                "push.triggered",
                title=title,
                content=content,
                priority=priority.value,
                target_type=target_type.value,
                target_id=target_id,
                rule_id=rule.id
            )

            from app.services.message_service import message_service
            send_request = SendMessageRequest(
                title=title,
                content=content,
                priority=priority,
                target_type=target_type,
                target_id=target_id
            )

            try:
                results = await message_service.send_message(send_request)
                messages_sent += len(results)
            except Exception as e:
                logger.error(f"规则 {rule.id} 触发消息发送失败: {e}")

        return EventReportResponse(
            event_type=request.event_type,
            matched_rules=matched_rules,
            messages_sent=messages_sent
        )

    def _evaluate_condition(self, condition: str, event_data: Dict[str, str]) -> bool:
        try:
            context = {}
            for key, value in event_data.items():
                parsed_value = self._parse_numeric_value(value)
                context[key] = parsed_value

            evaluated_condition = condition
            for key, value in context.items():
                pattern = r'\b' + re.escape(key) + r'\b'
                if isinstance(value, (int, float)):
                    replacement = str(value)
                else:
                    replacement = repr(value)
                evaluated_condition = re.sub(pattern, replacement, evaluated_condition)

            evaluated_condition = self._normalize_numeric_literals(evaluated_condition)

            return bool(eval(evaluated_condition, {"__builtins__": {}}, {}))
        except Exception as e:
            logger.warning(f"条件表达式求值失败: condition={condition}, error={e}")
            return False

    def _parse_numeric_value(self, value: str):
        if not isinstance(value, str):
            return value

        cleaned = re.sub(r'[^\d.\-]', '', value)
        if not cleaned or cleaned in ('.', '-', '-.'):
            return value

        try:
            if '.' in cleaned:
                return float(cleaned)
            else:
                return int(cleaned)
        except (ValueError, TypeError):
            return value

    def _normalize_numeric_literals(self, condition: str) -> str:
        return condition


rule_engine = RuleEngine()
