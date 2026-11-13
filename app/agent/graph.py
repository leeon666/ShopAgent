"""LangGraph 售后 Agent 工作流。"""
from __future__ import annotations

import time
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from .llm import complete_text
from .tools import check_return_policy, execute_tool, get_logistics, get_order

POLICY_INTENTS = {"refund", "return", "exchange", "damage"}
HIGH_RISK_INTENTS = {"refund", "return", "exchange", "damage"}


class AgentState(TypedDict, total=False):
    ticket_id: int
    user_id: int
    request_id: str
    message: str
    intent: str
    order_id: int
    tool_results: dict[str, Any]
    steps: list[dict]
    step_count: int
    max_steps: int
    token_budget: int
    tokens_used: int
    output: dict
    stop_reason: str | None
    _last_step_ts: float


def _record_step(state: AgentState, name: str, detail: dict | None = None) -> AgentState:
    now = time.perf_counter()
    last = state.get("_last_step_ts", now)
    state["_last_step_ts"] = now
    state.setdefault("steps", []).append(
        {
            "node": name,
            "duration_ms": round((now - last) * 1000, 2),
            "request_id": state.get("request_id"),
            "detail": detail or {},
        }
    )
    state["step_count"] = state.get("step_count", 0) + 1
    return state


def _detect_intent(message: str) -> str:
    text = (message or "").lower()
    if any(k in text for k in ("物流", "快递", "发货", "运输", "签收")):
        return "logistics"
    if any(k in text for k in ("换货", "换成", "置换")):
        return "exchange"
    if any(k in text for k in ("破损", "损坏", "少件", "少了一", "裂痕", "裂开", "碎", "瑕疵", "有问题")):
        return "damage"
    if any(k in text for k in ("退款", "退钱", "退费")):
        return "refund"
    if any(k in text for k in ("退货", "退掉", "可以退", "能退", "退吗")):
        return "return"
    return "other"


def parse_intent(state: AgentState) -> AgentState:
    state["_last_step_ts"] = time.perf_counter()
    state["intent"] = _detect_intent(state.get("message", ""))
    state["token_budget"] = state.get("token_budget", 2000)
    state["max_steps"] = state.get("max_steps", 8)
    state["tokens_used"] = state.get("tokens_used", 0)
    return _record_step(state, "parse_intent", {"intent": state["intent"]})


def load_order(state: AgentState) -> AgentState:
    result = execute_tool(
        "get_order",
        get_order,
        state["order_id"],
        state["user_id"],
        timeout_seconds=2,
    )
    state.setdefault("tool_results", {})["get_order"] = result
    state["tokens_used"] = state.get("tokens_used", 0) + 20
    return _record_step(state, "load_order", {"ok": result["ok"]})


def load_logistics(state: AgentState) -> AgentState:
    result = execute_tool(
        "get_logistics",
        get_logistics,
        state["order_id"],
        state["user_id"],
        timeout_seconds=2,
    )
    state.setdefault("tool_results", {})["get_logistics"] = result
    state["tokens_used"] = state.get("tokens_used", 0) + 20
    return _record_step(state, "load_logistics", {"ok": result["ok"]})


def retrieve_policy(state: AgentState) -> AgentState:
    result = execute_tool(
        "check_return_policy",
        check_return_policy,
        state.get("message", ""),
        3,
        timeout_seconds=3,
    )
    state.setdefault("tool_results", {})["check_return_policy"] = result
    state["tokens_used"] = state.get("tokens_used", 0) + 40
    return _record_step(state, "retrieve_policy", {"ok": result["ok"]})


def route_after_order(state: AgentState) -> str:
    if state.get("step_count", 0) >= state.get("max_steps", 8):
        return "stop"
    if state.get("tokens_used", 0) >= state.get("token_budget", 2000):
        return "stop"
    if state.get("intent") == "logistics":
        return "load_logistics"
    if state.get("intent") in POLICY_INTENTS:
        return "retrieve_policy"
    return "generate"


def generate(state: AgentState) -> AgentState:
    tools = state.get("tool_results", {})
    order_result = tools.get("get_order", {})
    order = order_result.get("data") if order_result.get("ok") else None
    logistics = tools.get("get_logistics", {}).get("data") if tools.get("get_logistics", {}).get("ok") else None
    policy_result = tools.get("check_return_policy", {})
    policies = policy_result.get("data") if policy_result.get("ok") else []

    missing: list[str] = []
    if not order:
        missing.append("无法读取订单，请确认订单是否存在且属于当前用户")
    if state.get("intent") in POLICY_INTENTS and not policies:
        missing.append("未检索到可用的售后政策依据")

    evidence = [
        {
            "claim": f"售后政策与「{state.get('intent')}」相关",
            "source": item.get("source") or item.get("title"),
            "quote": item.get("content", "")[:300],
            "document_id": item.get("document_id"),
        }
        for item in (policies or [])
    ]
    if order:
        evidence.append(
            {
                "claim": "订单状态与金额来自订单系统",
                "source": "orders",
                "quote": f"订单 {order['order_no']} 状态为 {order['status']}，金额 {order['total_amount']}",
            }
        )

    if not order:
        action = "request_order_info"
        confidence = 0.4
    elif state.get("intent") == "logistics":
        action = "provide_logistics_update"
        confidence = 0.8
    elif state.get("intent") in HIGH_RISK_INTENTS:
        action = "create_refund_review" if policies else "manual_review"
        confidence = 0.8 if policies else 0.5
    else:
        action = "provide_customer_service_answer"
        confidence = 0.7

    fallback = (
        f"已识别售后意图：{state.get('intent')}。"
        + (f"订单状态为 {order['status']}。" if order else "")
        + (f"已检索到 {len(policies)} 条政策依据。" if policies else "")
    )
    llm_summary = complete_text(
        "你是电商售后助手。只根据提供的订单与政策证据输出简洁中文摘要，不要编造事实。",
        f"顾客诉求：{state.get('message')}\n意图：{state.get('intent')}\n订单：{order}\n政策：{policies}",
    )

    policy_required = state.get("intent") in POLICY_INTENTS
    requires_approval = (
        state.get("intent") in HIGH_RISK_INTENTS
        or (policy_required and not policies)
        or confidence < 0.6
    )
    state["output"] = {
        "intent": state.get("intent"),
        "order_id": state.get("order_id"),
        "summary": llm_summary or fallback,
        "evidence": evidence,
        "missing_information": missing,
        "recommended_action": action,
        "requires_human_approval": requires_approval,
        "confidence": confidence,
        "logistics": logistics,
    }
    state["tokens_used"] = state.get("tokens_used", 0) + 80
    return _record_step(state, "generate", {"action": action})


def verify(state: AgentState) -> AgentState:
    output = state.get("output", {})
    if not output.get("evidence"):
        output["recommended_action"] = "manual_review"
        output["requires_human_approval"] = True
        output["confidence"] = min(output.get("confidence", 0.5), 0.4)
        state["stop_reason"] = "insufficient_evidence"
    elif output.get("requires_human_approval"):
        state["stop_reason"] = "human_approval_required"
    elif output.get("missing_information"):
        state["stop_reason"] = "needs_more_information"
    else:
        state["stop_reason"] = "completed"
    return _record_step(state, "verify", {"stop_reason": state["stop_reason"]})


def stop_node(state: AgentState) -> AgentState:
    state["stop_reason"] = "max_steps_or_token_budget"
    state["output"] = {
        "intent": state.get("intent", "other"),
        "summary": "Agent 已达到执行上限，已停止自动处理。",
        "evidence": [],
        "missing_information": [],
        "recommended_action": "manual_review",
        "requires_human_approval": True,
        "confidence": 0.0,
    }
    return _record_step(state, "stop")


def build_graph():
    graph = StateGraph(AgentState)
    graph.add_node("parse_intent", parse_intent)
    graph.add_node("load_order", load_order)
    graph.add_node("load_logistics", load_logistics)
    graph.add_node("retrieve_policy", retrieve_policy)
    graph.add_node("generate", generate)
    graph.add_node("verify", verify)
    graph.add_node("stop", stop_node)

    graph.add_edge(START, "parse_intent")
    graph.add_edge("parse_intent", "load_order")
    graph.add_conditional_edges(
        "load_order",
        route_after_order,
        {
            "load_logistics": "load_logistics",
            "retrieve_policy": "retrieve_policy",
            "generate": "generate",
            "stop": "stop",
        },
    )
    graph.add_edge("load_logistics", "generate")
    graph.add_edge("retrieve_policy", "generate")
    graph.add_edge("generate", "verify")
    graph.add_edge("verify", END)
    graph.add_edge("stop", END)
    return graph.compile()
