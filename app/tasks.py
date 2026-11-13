"""后台任务。"""
from .celery_app import celery_app
from .db import AuditLog, Order, Product, SessionLocal
from .observability import reset_request_id, set_request_id


@celery_app.task(bind=True, name="orders.expire_pending", max_retries=3, default_retry_delay=60)
def expire_pending_order(self, order_id: int, request_id: str | None = None) -> dict:
    token = set_request_id(request_id) if request_id else None
    try:
        try:
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
                        request_id=request_id,
                        action="order.expire",
                        target_type="order",
                        target_id=order.id,
                        detail={"order_no": order.order_no},
                    )
                )
                session.commit()
                return {"order_id": order_id, "cancelled": True, "skipped": False}
        except Exception as exc:
            raise self.retry(exc=exc)
    finally:
        if token is not None:
            reset_request_id(token)
