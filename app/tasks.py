"""后台任务。"""
from .celery_app import celery_app
from .db import AuditLog, Order, Product, SessionLocal


@celery_app.task(name="orders.expire_pending", max_retries=3, default_retry_delay=60)
def expire_pending_order(order_id: int) -> dict:
    with SessionLocal() as session:
        order = session.get(Order, order_id)
        if order is None or order.status != "pending":
            return {"order_id": order_id, "cancelled": False, "skipped": True}
        for item in order.items:
            product = session.get(Product, item.product_id)
            if product is not None:
                product.stock += item.quantity
                product.sales = max(0, product.sales - item.quantity)
        order.status = "cancelled"
        session.add(
            AuditLog(
                actor_id=None,
                actor_role="system",
                action="order.expire",
                target_type="order",
                target_id=order.id,
                detail={"order_no": order.order_no},
            )
        )
        session.commit()
        return {"order_id": order_id, "cancelled": True, "skipped": False}
