"""AgentRun 执行与序列化。"""
from datetime import datetime

from sqlalchemy.orm import Session

from ..audit import record_audit
from ..db import AgentRun, AfterSalesTicket
from .graph import build_graph


def execute_agent_run(
    session: Session,
    ticket: AfterSalesTicket,
    user: dict,
    message: str | None = None,
) -> AgentRun:
    input_message = message or ticket.reason or "请帮我处理售后"
    run = AgentRun(
        ticket_id=ticket.id,
        user_id=user["id"],
        status="running",
        input_message=input_message,
    )
    session.add(run)
    session.commit()
    session.refresh(run)
    try:
        result = build_graph().invoke(
            {
                "ticket_id": ticket.id,
                "user_id": user["id"],
                "message": input_message,
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
        run.stop_reason = result.get("stop_reason")
    except Exception as exc:  # pragma: no cover - 真实运行错误保存到记录
        run.status = "failed"
        run.error = str(exc)
        run.stop_reason = "error"
    run.finished_at = datetime.now()
    record_audit(
        session,
        user,
        "agent.run",
        "agent_run",
        run.id,
        {"ticket_id": ticket.id, "status": run.status, "stop_reason": run.stop_reason},
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
        "output": run.output,
        "steps": run.steps,
        "stop_reason": run.stop_reason,
        "error": run.error,
        "started_at": run.started_at,
        "finished_at": run.finished_at,
    }
