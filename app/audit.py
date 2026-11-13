"""审计日志与幂等记录。"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from .db import AuditLog, IdempotencyRecord


def record_audit(
    session: Session,
    actor: dict | None,
    action: str,
    target_type: str = "",
    target_id: int | None = None,
    detail: dict | None = None,
) -> None:
    session.add(
        AuditLog(
            actor_id=actor.get("id") if actor else None,
            actor_role=actor.get("role", "system") if actor else "system",
            action=action,
            target_type=target_type,
            target_id=target_id,
            detail=detail or {},
        )
    )


def get_idempotency(session: Session, user_id: int, key: str) -> IdempotencyRecord | None:
    return session.scalar(
        select(IdempotencyRecord).where(
            IdempotencyRecord.user_id == user_id,
            IdempotencyRecord.idempotency_key == key,
        )
    )


def save_idempotency(
    session: Session,
    user_id: int,
    key: str,
    action: str,
    resource_id: int | None,
) -> None:
    session.add(
        IdempotencyRecord(
            user_id=user_id,
            idempotency_key=key,
            action=action,
            resource_id=resource_id,
        )
    )
