"""售后工单路由：创建、查询、留言、取消与管理员处理。"""
import secrets
import time

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import AfterSalesMessage, AfterSalesTicket, Order, get_db
from ..schemas import AfterSalesCreateRequest, AfterSalesMessageRequest, AfterSalesReviewRequest
from .deps import get_current_admin, get_current_user

router = APIRouter(prefix="/api/after-sales", tags=["售后"])

ORDER_STATUS_ALLOWED = {"paid", "shipped", "completed"}

ADMIN_TRANSITIONS = {
    "pending": {"reviewing", "awaiting_user", "rejected"},
    "reviewing": {"awaiting_user", "rejected", "completed"},
}


def _gen_ticket_no() -> str:
    return "AS" + time.strftime("%Y%m%d%H%M%S") + secrets.token_hex(2).upper()


def _ticket_dict(ticket: AfterSalesTicket) -> dict:
    return {
        "id": ticket.id,
        "ticket_no": ticket.ticket_no,
        "user_id": ticket.user_id,
        "order_id": ticket.order_id,
        "type": ticket.type,
        "reason": ticket.reason,
        "status": ticket.status,
        "refund_amount": ticket.refund_amount,
        "resolution": ticket.resolution,
        "created_at": ticket.created_at,
        "updated_at": ticket.updated_at,
        "messages": [
            {
                "id": m.id,
                "sender_id": m.sender_id,
                "sender_role": m.sender_role,
                "content": m.content,
                "created_at": m.created_at,
            }
            for m in ticket.messages
        ],
        "order": {
            "id": ticket.order.id,
            "order_no": ticket.order.order_no,
            "status": ticket.order.status,
            "total_amount": ticket.order.total_amount,
        },
    }


def _get_owned_ticket(session: Session, ticket_id: int, user_id: int) -> AfterSalesTicket:
    ticket = session.get(AfterSalesTicket, ticket_id)
    if ticket is None:
        raise HTTPException(404, "售后工单不存在")
    if ticket.user_id != user_id:
        raise HTTPException(403, "无权查看该售后工单")
    return ticket


@router.post("", summary="创建售后工单")
def create_ticket(body: AfterSalesCreateRequest, user: dict = Depends(get_current_user), session: Session = Depends(get_db)):
    order = session.get(Order, body.order_id)
    if order is None:
        raise HTTPException(404, "订单不存在")
    if order.user_id != user["id"]:
        raise HTTPException(403, "无权为该订单申请售后")
    if order.status not in ORDER_STATUS_ALLOWED:
        raise HTTPException(400, f"订单状态为 {order.status}，不能申请售后")
    existing = session.scalar(
        select(AfterSalesTicket).where(
            AfterSalesTicket.order_id == body.order_id,
            AfterSalesTicket.status.not_in(["rejected", "completed", "cancelled"]),
        )
    )
    if existing:
        raise HTTPException(400, "该订单已有进行中的售后工单")
    ticket = AfterSalesTicket(
        ticket_no=_gen_ticket_no(),
        user_id=user["id"],
        order_id=body.order_id,
        type=body.type,
        reason=body.reason.strip(),
    )
    session.add(ticket)
    session.commit()
    session.refresh(ticket)
    return _ticket_dict(ticket)


@router.get("/my", summary="我的售后工单")
def my_tickets(user: dict = Depends(get_current_user), session: Session = Depends(get_db)):
    tickets = session.scalars(
        select(AfterSalesTicket).where(AfterSalesTicket.user_id == user["id"]).order_by(AfterSalesTicket.id.desc())
    ).all()
    return {"items": [_ticket_dict(t) for t in tickets]}


@router.get("/all", summary="全部售后工单（管理员）")
def all_tickets(user: dict = Depends(get_current_admin), session: Session = Depends(get_db)):
    tickets = session.scalars(select(AfterSalesTicket).order_by(AfterSalesTicket.id.desc())).all()
    return {"items": [_ticket_dict(t) for t in tickets]}


@router.get("/{ticket_id}", summary="售后工单详情")
def get_ticket(ticket_id: int, user: dict = Depends(get_current_user), session: Session = Depends(get_db)):
    ticket = session.get(AfterSalesTicket, ticket_id)
    if ticket is None:
        raise HTTPException(404, "售后工单不存在")
    if user["role"] != "admin" and ticket.user_id != user["id"]:
        raise HTTPException(403, "无权查看该售后工单")
    return _ticket_dict(ticket)


@router.post("/{ticket_id}/messages", summary="给售后工单留言")
def add_message(ticket_id: int, body: AfterSalesMessageRequest, user: dict = Depends(get_current_user), session: Session = Depends(get_db)):
    ticket = session.get(AfterSalesTicket, ticket_id)
    if ticket is None:
        raise HTTPException(404, "售后工单不存在")
    is_admin = user["role"] == "admin"
    if not is_admin and ticket.user_id != user["id"]:
        raise HTTPException(403, "无权操作该售后工单")
    if ticket.status in ("rejected", "completed", "cancelled"):
        raise HTTPException(400, "售后工单已结束，不能再留言")
    session.add(
        AfterSalesMessage(
            ticket_id=ticket_id,
            sender_id=user["id"],
            sender_role="admin" if is_admin else "user",
            content=body.content.strip(),
        )
    )
    session.commit()
    session.refresh(ticket)
    return _ticket_dict(ticket)


@router.post("/{ticket_id}/cancel", summary="用户取消售后工单")
def cancel_ticket(ticket_id: int, user: dict = Depends(get_current_user), session: Session = Depends(get_db)):
    ticket = _get_owned_ticket(session, ticket_id, user["id"])
    if ticket.status not in ("pending", "awaiting_user"):
        raise HTTPException(400, "当前状态不能取消")
    ticket.status = "cancelled"
    session.commit()
    return {"ok": True, "status": "cancelled"}


@router.post("/{ticket_id}/review", summary="管理员处理售后工单")
def review_ticket(ticket_id: int, body: AfterSalesReviewRequest, user: dict = Depends(get_current_admin), session: Session = Depends(get_db)):
    ticket = session.get(AfterSalesTicket, ticket_id)
    if ticket is None:
        raise HTTPException(404, "售后工单不存在")
    allowed = ADMIN_TRANSITIONS.get(ticket.status, set())
    if body.status not in allowed:
        raise HTTPException(400, f"不允许从 {ticket.status} 变更为 {body.status}")
    ticket.status = body.status
    ticket.resolution = body.resolution.strip()
    if body.refund_amount is not None:
        ticket.refund_amount = body.refund_amount
    session.commit()
    session.refresh(ticket)
    return _ticket_dict(ticket)
