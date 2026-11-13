"""AgentRun 执行与序列化。"""
import time
from datetime import datetime

from sqlalchemy.orm import Session

from ..audit import record_audit
from ..config import OPENAI_API_KEY, OPENAI_MODEL
from ..db import AgentRun, AfterSalesTicket, SessionLocal
from ..observability import get_request_id, new_request_id
from .graph import build_graph
from .llm import complete_text


def _conversation_context(ticket: AfterSalesTicket) -> tuple[str, bool]:
    history = [
        f"{message.sender_role}: {message.content}"
        for message in ticket.messages
        if message.content
    ]
    text = "\n".join(history[-20:])
    if len(text) <= 1200:
        return text, False
    summary = complete_text(
        "压缩电商售后多轮对话，保留订单号、商品问题、用户诉求、已提供证据和未解决事项。",
        text,
    )
    if not summary:
        summary = text[:600] + "\n...[较早对话已压缩]...\n" + text[-600:]
    return summary, True


def execute_agent_run(
    session: Session,
    ticket: AfterSalesTicket,
    user: dict,
    message: str | None = None,
) -> AgentRun:
    input_message = message or ticket.reason or "请帮我处理售后"
    context_summary, context_compressed = _conversation_context(ticket)
    request_id = get_request_id() or new_request_id()
    started = time.perf_counter()
    run = AgentRun(
        ticket_id=ticket.id,
        user_id=user["id"],
        status="running",
        input_message=input_message,
        request_id=request_id,
        model_name=OPENAI_MODEL if OPENAI_API_KEY else "rules-fallback",
        prompt_version="shopagent-agent-v1",
    )
    session.add(run)
    session.commit()
    session.refresh(run)
    try:
        result = build_graph().invoke(
            {
                "ticket_id": ticket.id,
                "user_id": user["id"],
                "request_id": request_id,
                "message": input_message,
                "context_summary": context_summary,
                "context_compressed": context_compressed,
                "order_id": ticket.order_id,
                "tool_results": {},
                "steps": [],
                "step_count": 0,
                "max_steps": 8,
                "token_budget": 2000,
                "tokens_used": 0,
                "stop_reason": None,
            }
        )
        run.status = "completed"
        run.output = result.get("output", {})
        run.steps = result.get("steps", [])
        run.tokens_used = result.get("tokens_used", 0)
        run.stop_reason = result.get("stop_reason")
    except Exception as exc:  # pragma: no cover - 真实运行错误保存到记录
        run.status = "failed"
        run.error = str(exc)
        run.stop_reason = "error"
    run.latency_ms = round((time.perf_counter() - started) * 1000, 2)
    run.finished_at = datetime.now()
    record_audit(
        session,
        user,
        "agent.run",
        "agent_run",
        run.id,
        {
            "ticket_id": ticket.id,
            "status": run.status,
            "stop_reason": run.stop_reason,
            "model_name": run.model_name,
            "latency_ms": run.latency_ms,
        },
    )
    session.commit()
    session.refresh(run)
    return run


def serialize_run(run: AgentRun) -> dict:
    return {
        "id": run.id,
        "ticket_id": run.ticket_id,
        "user_id": run.user_id,
        "status": run.status,
        "input_message": run.input_message,
        "request_id": run.request_id,
        "model_name": run.model_name,
        "prompt_version": run.prompt_version,
        "tokens_used": run.tokens_used,
        "latency_ms": run.latency_ms,
        "output": run.output,
        "steps": run.steps,
        "stop_reason": run.stop_reason,
        "error": run.error,
        "started_at": run.started_at,
        "finished_at": run.finished_at,
    }


def stream_agent_run_events(
    session: Session,
    ticket_id: int,
    user: dict,
    message: str | None = None,
):
    ticket = session.get(AfterSalesTicket, ticket_id)
    if ticket is None:
        raise ValueError("售后工单不存在")
    input_message = message or ticket.reason or "请帮我处理售后"
    context_summary, context_compressed = _conversation_context(ticket)
    request_id = get_request_id() or new_request_id()
    started = time.perf_counter()
    run = AgentRun(
        ticket_id=ticket.id,
        user_id=user["id"],
        status="running",
        input_message=input_message,
        request_id=request_id,
        model_name=OPENAI_MODEL if OPENAI_API_KEY else "rules-fallback",
        prompt_version="shopagent-agent-v1",
    )
    session.add(run)
    session.commit()
    session.refresh(run)
    yield {
        "event": "run_started",
        "run_id": run.id,
        "request_id": request_id,
        "model_name": run.model_name,
    }
    final_state = None
    try:
        for state in build_graph().stream(
            {
                "ticket_id": ticket.id,
                "user_id": user["id"],
                "request_id": request_id,
                "message": input_message,
                "context_summary": context_summary,
                "context_compressed": context_compressed,
                "order_id": ticket.order_id,
                "tool_results": {},
                "steps": [],
                "step_count": 0,
                "max_steps": 8,
                "token_budget": 2000,
                "tokens_used": 0,
                "stop_reason": None,
            },
            stream_mode="values",
        ):
            final_state = state
            steps = state.get("steps", [])
            if steps:
                yield {"event": "node", "run_id": run.id, "step": steps[-1]}
        run.status = "completed"
        run.output = final_state.get("output", {}) if final_state else {}
        run.steps = final_state.get("steps", []) if final_state else []
        run.tokens_used = final_state.get("tokens_used", 0) if final_state else 0
        run.stop_reason = final_state.get("stop_reason") if final_state else "empty_result"
    except GeneratorExit:
        run.status = "cancelled"
        run.stop_reason = "client_disconnected"
        raise
    except Exception as exc:  # pragma: no cover - 真实运行错误保存到记录
        run.status = "failed"
        run.error = str(exc)
        run.stop_reason = "error"
    finally:
        run.latency_ms = round((time.perf_counter() - started) * 1000, 2)
        run.finished_at = datetime.now()
        record_audit(
            session,
            user,
            "agent.stream",
            "agent_run",
            run.id,
            {
                "ticket_id": ticket.id,
                "status": run.status,
                "stop_reason": run.stop_reason,
                "latency_ms": run.latency_ms,
            },
        )
        session.commit()
        session.refresh(run)
    yield {"event": "completed", "run": serialize_run(run)}
