"""Celery tasks for deterministic ShopAgent post-approval workflows."""

import asyncio
import logging
from typing import Any

from celery import shared_task
from sqlalchemy import select

from app.db.models.shop import ActionProposal, AfterSalesTicket, AuditEvent, Order
from app.db.session import get_worker_db_context
from app.services.shop_state import transition_order, transition_ticket

logger = logging.getLogger(__name__)


async def _complete_approved_refunds() -> dict[str, int]:
    completed = 0
    skipped = 0
    async with get_worker_db_context() as db:
        proposals = list(
            (
                await db.execute(
                    select(ActionProposal)
                    .where(
                        ActionProposal.status == "approved",
                        ActionProposal.recommended_action == "approve_refund",
                    )
                    .with_for_update(skip_locked=True)
                )
            )
            .scalars()
            .all()
        )
        for proposal in proposals:
            ticket = await db.get(AfterSalesTicket, proposal.ticket_id)
            if ticket is None:
                skipped += 1
                continue
            order = await db.get(Order, ticket.order_id)
            if order is None:
                skipped += 1
                continue
            if order.status == "refunded" and ticket.status == "resolved":
                skipped += 1
                continue
            if order.status != "refund_pending":
                skipped += 1
                continue

            # The financial provider is simulated, but this transition is a
            # deterministic service action, never a model-generated write.
            order.status = transition_order(order.status, "refunded")
            ticket.status = transition_ticket(ticket.status, "resolved")
            ticket.resolution = (
                f"Approved proposal {proposal.proposal_no} executed by refund worker"
            )
            db.add(
                AuditEvent(
                    actor_id=None,
                    action="refund.completed",
                    entity_type="action_proposal",
                    entity_id=proposal.id,
                    request_id=None,
                    details={
                        "proposal_no": proposal.proposal_no,
                        "order_no": order.order_no,
                        "ticket_no": ticket.ticket_no,
                        "refund_amount": (
                            str(proposal.refund_amount)
                            if proposal.refund_amount is not None
                            else None
                        ),
                        "executor": "celery",
                    },
                )
            )
            completed += 1
        await db.flush()
    return {"completed": completed, "skipped": skipped}


@shared_task  # type: ignore[misc]
def complete_approved_refunds() -> dict[str, int]:
    """Execute approved refunds idempotently in a background worker."""
    result = asyncio.run(_complete_approved_refunds())
    logger.info("Approved refund reconciliation: %s", result)
    return result


@shared_task  # type: ignore[misc]
def ping_shop_worker() -> dict[str, Any]:
    """Lightweight worker readiness probe for local demos."""
    return {"status": "ok", "service": "shopagent-refunds"}
