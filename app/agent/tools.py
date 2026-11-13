"""Agent 可用工具：只读查询，带超时、重试和结果截断。"""
from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout

from sqlalchemy import select

from .. import rag
from ..db import Order, SessionLocal


def _truncate(value: str, limit: int = 2000) -> str:
    return value if len(value) <= limit else value[:limit] + "...[truncated]"


def get_order(order_id: int, user_id: int) -> dict | None:
    with SessionLocal() as session:
        order = session.scalar(select(Order).where(Order.id == order_id, Order.user_id == user_id))
        if order is None:
            return None
        return {
            "id": order.id,
            "order_no": order.order_no,
            "status": order.status,
            "total_amount": order.total_amount,
            "paid_at": order.paid_at.isoformat() if order.paid_at else None,
            "shipped_at": order.shipped_at.isoformat() if order.shipped_at else None,
            "items": [
                {
                    "product_name": item.product_name,
                    "quantity": item.quantity,
                    "price": item.price,
                }
                for item in order.items
            ],
        }


def get_logistics(order_id: int, user_id: int) -> dict | None:
    with SessionLocal() as session:
        order = session.scalar(select(Order).where(Order.id == order_id, Order.user_id == user_id))
        if order is None:
            return None
        events = [{"event": "订单已创建", "time": order.created_at.isoformat()}]
        if order.paid_at:
            events.append({"event": "支付成功", "time": order.paid_at.isoformat()})
        if order.shipped_at:
            events.append({"event": "已发货，物流运输中", "time": order.shipped_at.isoformat()})
        if order.status == "completed":
            events.append({"event": "已签收", "time": order.shipped_at.isoformat() if order.shipped_at else "未知"})
        return {"order_no": order.order_no, "status": order.status, "events": events}


def check_return_policy(query: str, top_k: int = 3) -> list[dict]:
    with SessionLocal() as session:
        results = rag.search(session, query, top_k=top_k)
    return [{**item, "content": _truncate(item["content"])} for item in results]


def execute_tool(name: str, fn, *args, timeout_seconds: float = 3.0, retries: int = 1, **kwargs) -> dict:
    started = time.perf_counter()
    last_error = None
    for attempt in range(retries + 1):
        try:
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(fn, *args, **kwargs)
                data = future.result(timeout=timeout_seconds)
            return {
                "ok": True,
                "tool": name,
                "data": data,
                "attempts": attempt + 1,
                "latency_ms": round((time.perf_counter() - started) * 1000, 2),
                "error": None,
            }
        except FutureTimeout:
            last_error = f"{name} 超时"
        except Exception as exc:  # pragma: no cover - 真实错误按工具记录
            last_error = str(exc)
    return {
        "ok": False,
        "tool": name,
        "data": None,
        "attempts": retries + 1,
        "latency_ms": round((time.perf_counter() - started) * 1000, 2),
        "error": last_error,
    }
