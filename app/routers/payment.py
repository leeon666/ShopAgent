"""支付路由：模拟第三方支付 + 回调（真实环境替换为微信/支付宝回调验签）"""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..audit import record_audit
from ..db import Order, Payment, get_db
from ..schemas import PaymentRequest
from .deps import get_current_user

router = APIRouter(prefix="/api/payment", tags=["支付"])


@router.post("/mock", summary="模拟支付并回调")
def mock_pay(body: PaymentRequest, user: dict = Depends(get_current_user), session: Session = Depends(get_db)):
    order = session.get(Order, body.order_id)
    if order is None:
        raise HTTPException(404, "订单不存在")
    if order.user_id != user["id"]:
        raise HTTPException(403, "无权操作该订单")
    if order.status != "pending":
        raise HTTPException(400, f"当前订单状态为 {order.status}，不能支付")
    session.add(Payment(order_id=order.id, amount=order.total_amount, pay_type=body.pay_type, status="success"))
    order.status = "paid"
    order.paid_at = datetime.now()
    order_no = order.order_no
    record_audit(session, user, "payment.mock", "order", order.id, {"order_no": order_no})
    session.commit()
    return {"ok": True, "message": "支付成功", "order_no": order_no, "status": "paid"}
