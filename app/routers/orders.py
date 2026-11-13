"""订单路由（需登录）：下单 / 我的订单 / 取消。"""
import secrets
import time
from datetime import datetime

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import tasks
from ..audit import get_idempotency, record_audit, save_idempotency
from ..celery_app import celery_app
from ..db import CartItem, Order, OrderItem, Product, get_db
from ..observability import get_request_id
from .deps import get_current_user

router = APIRouter(prefix="/api/orders", tags=["订单"])


def _gen_order_no() -> str:
    return time.strftime("%Y%m%d%H%M%S") + secrets.token_hex(2).upper()


def _order_detail(session: Session, order_id: int, user_id: int | None = None) -> dict:
    order = session.get(Order, order_id)
    if order is None:
        raise HTTPException(404, "订单不存在")
    if user_id is not None and order.user_id != user_id:
        raise HTTPException(403, "无权查看该订单")
    items = [
        {
            "id": i.id,
            "product_id": i.product_id,
            "product_name": i.product_name,
            "price": i.price,
            "quantity": i.quantity,
        }
        for i in order.items
    ]
    return {
        "id": order.id,
        "order_no": order.order_no,
        "user_id": order.user_id,
        "total_amount": order.total_amount,
        "status": order.status,
        "created_at": order.created_at,
        "paid_at": order.paid_at,
        "shipped_at": order.shipped_at,
        "items": items,
    }


@router.post("", summary="从购物车下单")
def create_order(
    user: dict = Depends(get_current_user),
    session: Session = Depends(get_db),
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
):
    if idempotency_key:
        existing = get_idempotency(session, user["id"], idempotency_key)
        if existing and existing.resource_id:
            return _order_detail(session, existing.resource_id)
    cart_rows = session.execute(
        select(CartItem, Product).join(Product, Product.id == CartItem.product_id).where(CartItem.user_id == user["id"])
    ).all()
    if not cart_rows:
        raise HTTPException(400, "购物车为空")

    total = 0.0
    for _item, product in cart_rows:
        if product.status != "on":
            raise HTTPException(400, f"商品「{product.name}」已下架，请从购物车移除")
        if _item.quantity > product.stock:
            raise HTTPException(400, f"商品「{product.name}」库存不足，当前库存 {product.stock}")
        total += product.price * _item.quantity

    order = Order(order_no=_gen_order_no(), user_id=user["id"], total_amount=round(total, 2))
    session.add(order)
    session.flush()
    for item, product in cart_rows:
        session.add(
            OrderItem(
                order_id=order.id,
                product_id=product.id,
                product_name=product.name,
                price=product.price,
                quantity=item.quantity,
            )
        )
        product.stock -= item.quantity
        product.sales += item.quantity
        session.delete(item)
    if idempotency_key:
        save_idempotency(session, user["id"], idempotency_key, "order.create", order.id)
    record_audit(session, user, "order.create", "order", order.id, {"order_no": order.order_no})
    session.commit()
    if not celery_app.conf.task_always_eager:
        tasks.expire_pending_order.apply_async(args=[order.id, get_request_id()], countdown=1800)
    return _order_detail(session, order.id)


@router.get("/my", summary="我的订单")
def my_orders(user: dict = Depends(get_current_user), session: Session = Depends(get_db)):
    orders = session.scalars(select(Order).where(Order.user_id == user["id"]).order_by(Order.id.desc())).all()
    return {"items": [_order_detail(session, o.id) for o in orders]}


@router.get("/{order_id}", summary="订单详情")
def get_order(order_id: int, user: dict = Depends(get_current_user), session: Session = Depends(get_db)):
    return _order_detail(session, order_id, user["id"])


@router.post("/{order_id}/cancel", summary="取消订单（仅待付款）")
def cancel_order(order_id: int, user: dict = Depends(get_current_user), session: Session = Depends(get_db)):
    order = session.get(Order, order_id)
    if order is None:
        raise HTTPException(404, "订单不存在")
    if order.user_id != user["id"]:
        raise HTTPException(403, "无权操作该订单")
    if order.status != "pending":
        raise HTTPException(400, "仅待付款订单可取消")
    order.status = "cancelled"
    for item in order.items:
        product = session.get(Product, item.product_id)
        if product is not None:
            product.stock += item.quantity
            product.sales = max(0, product.sales - item.quantity)
    record_audit(session, user, "order.cancel", "order", order.id, {"order_no": order.order_no})
    session.commit()
    return {"ok": True, "status": "cancelled"}
