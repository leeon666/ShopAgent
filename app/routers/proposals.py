"""Agent 执行提案与人工确认。"""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..audit import record_audit
from ..db import ActionProposal, AfterSalesTicket, get_db
from ..schemas import ProposalDecisionRequest
from .deps import get_current_admin, get_current_user

router = APIRouter(prefix="/api/proposals", tags=["执行提案"])


def _serialize(proposal: ActionProposal) -> dict:
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


@router.get("", summary="提案列表（管理员）")
def list_proposals(
    status: str | None = None,
    admin: dict = Depends(get_current_admin),
    session: Session = Depends(get_db),
):
    stmt = select(ActionProposal).order_by(ActionProposal.id.desc())
    if status:
        stmt = stmt.where(ActionProposal.status == status)
    proposals = session.scalars(stmt).all()
    return {"items": [_serialize(proposal) for proposal in proposals]}


@router.get("/{proposal_id}", summary="提案详情")
def get_proposal(
    proposal_id: int,
    user: dict = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    proposal = session.get(ActionProposal, proposal_id)
    if proposal is None:
        raise HTTPException(404, "执行提案不存在")
    if user["role"] != "admin" and proposal.created_by_id != user["id"]:
        raise HTTPException(403, "无权查看该执行提案")
    return _serialize(proposal)


@router.post("/{proposal_id}/approve", summary="批准执行提案")
def approve_proposal(
    proposal_id: int,
    body: ProposalDecisionRequest | None = None,
    admin: dict = Depends(get_current_admin),
    session: Session = Depends(get_db),
):
    proposal = session.get(ActionProposal, proposal_id)
    if proposal is None:
        raise HTTPException(404, "执行提案不存在")
    if proposal.status != "pending":
        raise HTTPException(400, f"提案状态为 {proposal.status}，不能批准")
    ticket = session.get(AfterSalesTicket, proposal.ticket_id)
    if ticket is None:
        raise HTTPException(404, "售后工单不存在")
    if ticket.status not in ("pending", "reviewing"):
        raise HTTPException(400, f"工单状态为 {ticket.status}，不能批准")

    proposal.status = "approved"
    proposal.decision_note = (body.decision_note if body else "") or "管理员批准执行"
    proposal.reviewed_by_id = admin["id"]
    proposal.reviewed_at = datetime.now()
    ticket.status = "completed"
    ticket.refund_amount = proposal.payload.get("refund_amount")
    ticket.resolution = proposal.decision_note
    record_audit(
        session,
        admin,
        "proposal.approve",
        "action_proposal",
        proposal.id,
        {"ticket_id": ticket.id, "refund_amount": ticket.refund_amount},
    )
    session.commit()
    session.refresh(proposal)
    return _serialize(proposal)


@router.post("/{proposal_id}/reject", summary="驳回执行提案")
def reject_proposal(
    proposal_id: int,
    body: ProposalDecisionRequest | None = None,
    admin: dict = Depends(get_current_admin),
    session: Session = Depends(get_db),
):
    proposal = session.get(ActionProposal, proposal_id)
    if proposal is None:
        raise HTTPException(404, "执行提案不存在")
    if proposal.status != "pending":
        raise HTTPException(400, f"提案状态为 {proposal.status}，不能驳回")
    ticket = session.get(AfterSalesTicket, proposal.ticket_id)
    if ticket is None:
        raise HTTPException(404, "售后工单不存在")

    proposal.status = "rejected"
    proposal.decision_note = (body.decision_note if body else "") or "管理员驳回提案"
    proposal.reviewed_by_id = admin["id"]
    proposal.reviewed_at = datetime.now()
    ticket.status = "rejected"
    ticket.resolution = proposal.decision_note
    record_audit(
        session,
        admin,
        "proposal.reject",
        "action_proposal",
        proposal.id,
        {"ticket_id": ticket.id},
    )
    session.commit()
    session.refresh(proposal)
    return _serialize(proposal)
