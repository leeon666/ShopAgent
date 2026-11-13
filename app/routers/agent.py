"""售后 Agent 运行接口。"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..agent.service import execute_agent_run, serialize_run
from ..db import AgentRun, AfterSalesTicket, get_db
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
