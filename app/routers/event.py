from typing import List
from fastapi import APIRouter

from app.models.rule import EventReportRequest, EventReportResponse, PushRuleResponse
from app.services.rule_engine import rule_engine
from app.core.event_bus import event_bus

router = APIRouter(prefix="/api/events", tags=["推送规则"])


@router.post("/report", response_model=EventReportResponse, summary="上报事件")
async def report_event(request: EventReportRequest):
    """
    上报事件，服务端匹配推送规则后自动推送消息
    - **event_type**: 事件类型（如 login_fail、order_created、stock_changed）
    - **event_data**: 事件数据，用于条件匹配和模板参数替换
    - **target_user_id**: 可选，指定目标用户ID（覆盖规则中的 target_id）
    """
    await event_bus.publish_event("event.reported", **request.model_dump())
    return await rule_engine.process_event(request)


@router.get("/rules", response_model=List[PushRuleResponse], summary="获取所有推送规则")
def list_rules():
    """
    获取所有推送规则列表
    """
    return rule_engine.list_rules()


@router.get("/rules/{rule_id}", response_model=PushRuleResponse, summary="获取规则详情")
def get_rule(rule_id: str):
    """
    根据规则ID获取规则详情
    """
    return rule_engine.get_rule_response(rule_id)


@router.put("/rules/{rule_id}/toggle", response_model=PushRuleResponse, summary="启用/禁用规则")
def toggle_rule(rule_id: str, enabled: bool = True):
    """
    启用或禁用推送规则
    - **rule_id**: 规则ID
    - **enabled**: 是否启用
    """
    return rule_engine.toggle_rule(rule_id, enabled)
