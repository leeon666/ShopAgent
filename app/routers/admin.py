"""管理后台路由（需管理员）：商品管理 / 订单处理 / 数据统计。"""
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..audit import record_audit
from ..db import AuditLog, CartItem, Category, Order, Product, User, get_db
from ..schemas import ProductCreateRequest, ProductUpdateRequest, StatusUpdateRequest, StockUpdateRequest
from .deps import get_current_admin

router = APIRouter(prefix="/api/admin", tags=["管理后台"])


@router.get("/audit-logs", summary="审计日志")
def audit_logs(
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    admin: dict = Depends(get_current_admin),
    session: Session = Depends(get_db),
):
    total = session.scalar(select(func.count()).select_from(AuditLog)) or 0
    rows = session.scalars(select(AuditLog).order_by(AuditLog.id.desc()).offset((page - 1) * size).limit(size)).all()
    items = [
        {
            "id": log.id,
            "actor_id": log.actor_id,
            "actor_role": log.actor_role,
            "request_id": log.request_id,
            "action": log.action,
            "target_type": log.target_type,
            "target_id": log.target_id,
            "detail": log.detail,
            "created_at": log.created_at,
        }
        for log in rows
    ]
    return {"items": items, "total": total, "page": page, "size": size}


@router.post("/products", summary="新增商品")
def create_product(body: ProductCreateRequest, admin: dict = Depends(get_current_admin), session: Session = Depends(get_db)):
    if session.get(Category, body.category_id) is None:
        raise HTTPException(400, "分类不存在")
    product = Product(
        category_id=body.category_id,
        name=body.name,
        description=body.description,
        price=body.price,
        stock=body.stock,
        image=body.image,
    )
    session.add(product)
    session.commit()
    session.refresh(product)
    record_audit(session, admin, "product.create", "product", product.id, {"name": product.name})
    session.commit()
    return {"ok": True, "id": product.id}


@router.put("/products/{product_id}", summary="更新商品")
def update_product(product_id: int, body: ProductUpdateRequest, admin: dict = Depends(get_current_admin), session: Session = Depends(get_db)):
    product = session.get(Product, product_id)
    if product is None:
        raise HTTPException(404, "商品不存在")
    changed = False
    for field in ("category_id", "name", "description", "price", "image"):
        value = getattr(body, field)
        if value is not None:
            setattr(product, field, value)
            changed = True
    if not changed:
        raise HTTPException(400, "没有需要更新的字段")
    record_audit(session, admin, "product.update", "product", product.id, {"name": product.name})
    session.commit()
    return {"ok": True}


@router.patch("/products/{product_id}/stock", summary="调整库存")
def update_stock(product_id: int, body: StockUpdateRequest, admin: dict = Depends(get_current_admin), session: Session = Depends(get_db)):
    product = session.get(Product, product_id)
    if product is None:
        raise HTTPException(404, "商品不存在")
    product.stock = body.stock
    record_audit(session, admin, "product.stock_update", "product", product.id, {"stock": body.stock})
    session.commit()
    return {"ok": True, "stock": body.stock}


@router.patch("/products/{product_id}/status", summary="上架/下架")
def update_status(product_id: int, body: StatusUpdateRequest, admin: dict = Depends(get_current_admin), session: Session = Depends(get_db)):
    if body.status not in ("on", "off"):
        raise HTTPException(400, "status 只能是 on/off")
    product = session.get(Product, product_id)
    if product is None:
        raise HTTPException(404, "商品不存在")
    product.status = body.status
    record_audit(session, admin, "product.status_update", "product", product.id, {"status": body.status})
    session.commit()
    return {"ok": True, "status": body.status}


@router.delete("/products/{product_id}", summary="删除商品")
def delete_product(product_id: int, admin: dict = Depends(get_current_admin), session: Session = Depends(get_db)):
    product = session.get(Product, product_id)
    if product is None:
        raise HTTPException(404, "商品不存在")
    for item in session.scalars(select(CartItem).where(CartItem.product_id == product_id)).all():
        session.delete(item)
    session.delete(product)
    record_audit(session, admin, "product.delete", "product", product_id, {"name": product.name})
    session.commit()
    return {"ok": True}


@router.get("/orders", summary="全部订单")
def admin_orders(
    status: str | None = None,
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    admin: dict = Depends(get_current_admin),
    session: Session = Depends(get_db),
):
    filters = []
    if status:
        filters.append(Order.status == status)
    total = session.scalar(select(func.count()).select_from(Order).where(*filters)) or 0
    rows = session.execute(
        select(Order, User.username)
        .join(User, User.id == Order.user_id)
        .where(*filters)
        .order_by(Order.id.desc())
        .offset((page - 1) * size)
        .limit(size)
    ).all()
    items = []
    for order, username in rows:
        data = {
            "id": order.id,
            "order_no": order.order_no,
            "user_id": order.user_id,
            "username": username,
            "total_amount": order.total_amount,
            "status": order.status,
            "created_at": order.created_at,
            "paid_at": order.paid_at,
            "shipped_at": order.shipped_at,
            "items": [
                {
                    "id": i.id,
                    "product_id": i.product_id,
                    "product_name": i.product_name,
                    "price": i.price,
                    "quantity": i.quantity,
                }
                for i in order.items
            ],
        }
        items.append(data)
    return {"items": items, "total": total, "page": page, "size": size}


@router.post("/orders/{order_id}/ship", summary="发货")
def ship_order(order_id: int, admin: dict = Depends(get_current_admin), session: Session = Depends(get_db)):
    order = session.get(Order, order_id)
    if order is None:
        raise HTTPException(404, "订单不存在")
    if order.status != "paid":
        raise HTTPException(400, "仅已付款订单可发货")
    order.status = "shipped"
    order.shipped_at = datetime.now()
    record_audit(session, admin, "order.ship", "order", order.id, {"order_no": order.order_no})
    session.commit()
    return {"ok": True, "status": "shipped"}


@router.post("/orders/{order_id}/complete", summary="完成订单")
def complete_order(order_id: int, admin: dict = Depends(get_current_admin), session: Session = Depends(get_db)):
    order = session.get(Order, order_id)
    if order is None:
        raise HTTPException(404, "订单不存在")
    if order.status not in ("paid", "shipped"):
        raise HTTPException(400, "仅已付款/已发货订单可完成")
    order.status = "completed"
    record_audit(session, admin, "order.complete", "order", order.id, {"order_no": order.order_no})
    session.commit()
    return {"ok": True, "status": "completed"}


@router.get("/stats", summary="经营统计")
def stats(admin: dict = Depends(get_current_admin), session: Session = Depends(get_db)):
    revenue = session.scalar(
        select(func.coalesce(func.sum(Order.total_amount), 0)).where(Order.status.in_(["paid", "shipped", "completed"]))
    ) or 0
    order_total = session.scalar(select(func.count()).select_from(Order)) or 0
    todo = session.scalar(select(func.count()).select_from(Order).where(Order.status.in_(["pending", "paid"]))) or 0
    prod_total = session.scalar(select(func.count()).select_from(Product)) or 0
    low_stock = session.scalar(
        select(func.count()).select_from(Product).where(Product.status == "on", Product.stock <= 10)
    ) or 0
    top = [
        {"name": p.name, "sales": p.sales, "price": p.price, "stock": p.stock}
        for p in session.scalars(select(Product).order_by(Product.sales.desc()).limit(5)).all()
    ]
    since = datetime.now() - timedelta(days=6)
    trend_rows = session.execute(
        select(func.date(Order.paid_at), func.sum(Order.total_amount))
        .where(Order.paid_at.is_not(None), Order.paid_at >= since)
        .group_by(func.date(Order.paid_at))
        .order_by(func.date(Order.paid_at))
    ).all()
    trend = [{"date": str(day), "amount": round(float(amount), 2)} for day, amount in trend_rows]
    status_rows = session.execute(select(Order.status, func.count()).group_by(Order.status)).all()
    by_status = {status: count for status, count in status_rows}
    return {
        "revenue": round(float(revenue), 2),
        "order_total": order_total,
        "todo_orders": todo,
        "product_total": prod_total,
        "low_stock": low_stock,
        "top_products": top,
        "trend": trend,
        "by_status": by_status,
    }
