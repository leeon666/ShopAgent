"""Celery 应用，缺少 Redis 时使用 eager 模式。"""
from celery import Celery

from .config import REDIS_URL

task_always_eager = not bool(REDIS_URL)

celery_app = Celery(
    "shopagent",
    broker=REDIS_URL or "memory://",
    backend=REDIS_URL or "cache+memory://",
)
celery_app.conf.update(
    task_always_eager=task_always_eager,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Asia/Shanghai",
    enable_utc=True,
)
