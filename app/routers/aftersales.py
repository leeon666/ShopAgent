"""售后工单路由：创建、查询、留言、取消与管理员处理。"""
import secrets
import time

from fastapi import APIRouter, Depends, HTTPException

from .. import db
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


def _ticket_detail(conn, ticket_id: int, user_id: int | None = None, is_admin: bool = False):
    row = conn.execute("SELECT * FROM after_sales_tickets WHERE id=?", (ticket_id,)).fetchone()
    if row is None:
        raise HTTPException(404, "售后工单不存在")
    if not is_admin and user_id is not None and row["user_id"] != user_id:
        raise HTTPException(403, "无权查看该售后工单")
    data = db.row_to_dict(row)
    messages = conn.execute(
        "SELECT * FROM after_sales_messages WHERE ticket_id=? ORDER BY id ASC",
        (ticket_id,),
    ).fetchall()
    data["messages"] = [db.row_to_dict(m) for m in messages]
    order = conn.execute("SELECT * FROM orders WHERE id=?", (row["order_id"],)).fetchone()
    data["order"] = db.row_to_dict(order)
    return data


@router.post("", summary="创建售后工单")
def create_ticket(body: AfterSalesCreateRequest, user: dict = Depends(get_current_user)):
    with db.get_conn() as conn:
        order = conn.execute("SELECT * FROM orders WHERE id=?", (body.order_id,)).fetchone()
        if order is None:
            raise HTTPException(404, "订单不存在")
        if order["user_id"] != user["id"]:
            raise HTTPException(403, "无权为该订单申请售后")
        if order["status"] not in ORDER_STATUS_ALLOWED:
            raise HTTPException(400, f"订单状态为 {order['status']}，不能申请售后")
        existing = conn.execute(
            "SELECT id FROM after_sales_tickets WHERE order_id=? AND status NOT IN ('rejected','completed','cancelled')",
            (body.order_id,),
        ).fetchone()
        if existing:
            raise HTTPException(400, "该订单已有进行中的售后工单")
        ticket_no = _gen_ticket_no()
        cur = conn.execute(
            """INSERT INTO after_sales_tickets(ticket_no, user_id, order_id, type, reason)
               VALUES(?,?,?,?,?)""",
            (ticket_no, user["id"], body.order_id, body.type, body.reason.strip()),
        )
        ticket_id = cur.lastrowid
    return _ticket_detail(conn, ticket_id, user["id"])


@router.get("/my", summary="我的售后工单")
def my_tickets(user: dict = Depends(get_current_user)):
    with db.get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM after_sales_tickets WHERE user_id=? ORDER BY id DESC",
            (user["id"],),
        ).fetchall()
        items = [db.row_to_dict(r) for r in rows]
    return {"items": items}


@router.get("/all", summary="全部售后工单（管理员）")
def all_tickets(user: dict = Depends(get_current_admin)):
    with db.get_conn() as conn:
        rows = conn.execute("SELECT * FROM after_sales_tickets ORDER BY id DESC").fetchall()
        items = [db.row_to_dict(r) for r in rows]
    return {"items": items}


@router.get("/{ticket_id}", summary="售后工单详情")
def get_ticket(ticket_id: int, user: dict = Depends(get_current_user)):
    with db.get_conn() as conn:
        return _ticket_detail(conn, ticket_id, user["id"], is_admin=user["role"] == "admin")


@router.post("/{ticket_id}/messages", summary="给售后工单留言")
def add_message(ticket_id: int, body: AfterSalesMessageRequest, user: dict = Depends(get_current_user)):
    with db.get_conn() as conn:
        row = conn.execute("SELECT * FROM after_sales_tickets WHERE id=?", (ticket_id,)).fetchone()
        if row is None:
            raise HTTPException(404, "售后工单不存在")
        is_admin = user["role"] == "admin"
        if not is_admin and row["user_id"] != user["id"]:
            raise HTTPException(403, "无权操作该售后工单")
        if row["status"] in ("rejected", "completed", "cancelled"):
            raise HTTPException(400, "售后工单已结束，不能再留言")
        conn.execute(
            "INSERT INTO after_sales_messages(ticket_id, sender_id, sender_role, content) VALUES(?,?,?,?)",
            (ticket_id, user["id"], "admin" if is_admin else "user", body.content.strip()),
        )
    return _ticket_detail(conn, ticket_id, user["id"], is_admin=is_admin)


@router.post("/{ticket_id}/cancel", summary="用户取消售后工单")
def cancel_ticket(ticket_id: int, user: dict = Depends(get_current_user)):
    with db.get_conn() as conn:
        row = conn.execute("SELECT * FROM after_sales_tickets WHERE id=?", (ticket_id,)).fetchone()
        if row is None:
            raise HTTPException(404, "售后工单不存在")
        if row["user_id"] != user["id"]:
            raise HTTPException(403, "无权操作该售后工单")
        if row["status"] not in ("pending", "awaiting_user"):
            raise HTTPException(400, "当前状态不能取消")
        conn.execute(
            "UPDATE after_sales_tickets SET status='cancelled', updated_at=datetime('now','localtime') WHERE id=?",
            (ticket_id,),
        )
    return {"ok": True, "status": "cancelled"}


@router.post("/{ticket_id}/review", summary="管理员处理售后工单")
def review_ticket(ticket_id: int, body: AfterSalesReviewRequest, user: dict = Depends(get_current_admin)):
    with db.get_conn() as conn:
        row = conn.execute("SELECT * FROM after_sales_tickets WHERE id=?", (ticket_id,)).fetchone()
        if row is None:
            raise HTTPException(404, "售后工单不存在")
        allowed = ADMIN_TRANSITIONS.get(row["status"], set())
        if body.status not in allowed:
            raise HTTPException(400, f"不允许从 {row['status']} 变更为 {body.status}")
        conn.execute(
            """UPDATE after_sales_tickets
               SET status=?, resolution=?, refund_amount=?, updated_at=datetime('now','localtime')
               WHERE id=?""",
            (body.status, body.resolution.strip(), body.refund_amount, ticket_id),
        )
    return _ticket_detail(conn, ticket_id, is_admin=True)
