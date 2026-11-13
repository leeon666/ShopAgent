"""售后 Agent 运行接口。"""
import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..agent.service import execute_agent_run, serialize_run, stream_agent_run_events
from ..audit import record_audit
from ..db import ActionProposal, AgentRun, AfterSalesTicket, SessionLocal, get_db
from ..schemas import AgentRunRequest
from .deps import get_current_user

router = APIRouter(prefix="/api/agent-runs", tags=["售后 Agent"])


@router.post("/tickets/{ticket_id}", summary="为售后工单运行 Agent")
def run_agent(
    ticket_id: int,
    body: AgentRunRequest,
    user: dict = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    ticket = session.get(AfterSalesTicket, ticket_id)
    if ticket is None:
        raise HTTPException(404, "售后工单不存在")
    if user["role"] != "admin" and ticket.user_id != user["id"]:
        raise HTTPException(403, "无权运行该工单的 Agent")
    run = execute_agent_run(session, ticket, user, body.message)
    return serialize_run(run)


@router.post("/tickets/{ticket_id}/stream", summary="流式运行售后 Agent")
def stream_agent(
    ticket_id: int,
    body: AgentRunRequest,
    user: dict = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    ticket = session.get(AfterSalesTicket, ticket_id)
    if ticket is None:
        raise HTTPException(404, "售后工单不存在")
    if user["role"] != "admin" and ticket.user_id != user["id"]:
        raise HTTPException(403, "无权运行该工单的 Agent")

    def event_generator():
        with SessionLocal() as stream_session:
            for event in stream_agent_run_events(stream_session, ticket_id, user, body.message):
                yield f"data: {json.dumps(event, ensure_ascii=False, default=str)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/{run_id}", summary="查询 Agent 运行结果")
def get_agent_run(
    run_id: int,
    user: dict = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    run = session.get(AgentRun, run_id)
    if run is None:
        raise HTTPException(404, "Agent 运行记录不存在")
    if user["role"] != "admin" and run.user_id != user["id"]:
        raise HTTPException(403, "无权查看该 Agent 运行记录")
    return serialize_run(run)


@router.post("/{run_id}/proposals", summary="从 Agent 结果创建执行提案")
def create_proposal(
    run_id: int,
    user: dict = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    run = session.get(AgentRun, run_id)
    if run is None:
        raise HTTPException(404, "Agent 运行记录不存在")
    if user["role"] != "admin" and run.user_id != user["id"]:
        raise HTTPException(403, "无权为该运行创建提案")
    if run.status != "completed":
        raise HTTPException(400, "Agent 尚未完成")
    if not (run.output or {}).get("requires_human_approval"):
        raise HTTPException(400, "该结果不需要人工执行提案")

    existing = session.scalar(select(ActionProposal).where(ActionProposal.agent_run_id == run.id))
    if existing:
        return _serialize_proposal(existing)

    ticket = session.get(AfterSalesTicket, run.ticket_id)
    if ticket is None:
        raise HTTPException(404, "售后工单不存在")
    output = run.output or {}
    proposal = ActionProposal(
        ticket_id=ticket.id,
        agent_run_id=run.id,
        created_by_id=user["id"],
        action_type="refund_review",
        payload={
            "recommended_action": output.get("recommended_action"),
            "confidence": output.get("confidence"),
            "summary": output.get("summary"),
            "refund_amount": ticket.order.total_amount,
            "evidence_count": len(output.get("evidence", [])),
        },
    )
    session.add(proposal)
    session.flush()
    record_audit(
        session,
        user,
        "proposal.create",
        "action_proposal",
        proposal.id,
        {"ticket_id": ticket.id, "agent_run_id": run.id, "action_type": proposal.action_type},
    )
    session.commit()
    session.refresh(proposal)
    return _serialize_proposal(proposal)


def _serialize_proposal(proposal: ActionProposal) -> dict:
    return {
        "id": proposal.id,
        "ticket_id": proposal.ticket_id,
        "agent_run_id": proposal.agent_run_id,
        "created_by_id": proposal.created_by_id,
        "action_type": proposal.action_type,
        "payload": proposal.payload,
        "status": proposal.status,
        "decision_note": proposal.decision_note,
        "reviewed_by_id": proposal.reviewed_by_id,
        "created_at": proposal.created_at,
        "reviewed_at": proposal.reviewed_at,
    }
