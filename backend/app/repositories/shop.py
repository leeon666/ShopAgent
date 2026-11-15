"""ShopAgent data-access layer."""

import secrets
import time
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.shop import (
    ActionProposal,
    AfterSalesMessage,
    AfterSalesTicket,
    AgentRun,
    AgentStep,
    AuditEvent,
    Order,
    OrderItem,
    Product,
)


def _order_number() -> str:
    return f"ORD-{time.strftime('%Y%m%d%H%M%S')}-{secrets.token_hex(2).upper()}"


def _ticket_number() -> str:
    return f"AS-{time.strftime('%Y%m%d%H%M%S')}-{secrets.token_hex(2).upper()}"


def _proposal_number() -> str:
    return f"AP-{time.strftime('%Y%m%d%H%M%S')}-{secrets.token_hex(2).upper()}"


async def list_products(db: AsyncSession, skip: int, limit: int) -> tuple[list[Product], int]:
    total = (await db.execute(select(func.count()).select_from(Product))).scalar_one()
    products = (
        (await db.execute(select(Product).order_by(Product.created_at.desc()).offset(skip).limit(limit)))
        .scalars()
        .all()
    )
    return list(products), int(total)


async def create_product(
    db: AsyncSession,
    *,
    name: str,
    description: str,
    price: Decimal,
    stock: int,
) -> Product:
    product = Product(name=name, description=description, price=price, stock=stock)
    db.add(product)
    await db.flush()
    await db.refresh(product)
    return product


async def get_product(db: AsyncSession, product_id: UUID) -> Product | None:
    return (await db.execute(select(Product).where(Product.id == product_id))).scalar_one_or_none()


async def get_product_for_update(db: AsyncSession, product_id: UUID) -> Product | None:
    return (
        await db.execute(select(Product).where(Product.id == product_id).with_for_update())
    ).scalar_one_or_none()


async def create_order(
    db: AsyncSession,
    *,
    user_id: UUID,
    items: list[tuple[Product, int]],
) -> Order:
    total = sum((product.price * quantity for product, quantity in items), Decimal("0"))
    order = Order(order_no=_order_number(), user_id=user_id, total_amount=total)
    db.add(order)
    await db.flush()
    for product, quantity in items:
        db.add(
            OrderItem(
                order_id=order.id,
                product_id=product.id,
                product_name=product.name,
                price=product.price,
                quantity=quantity,
            )
        )
        product.stock -= quantity
    await db.flush()
    await db.refresh(order)
    return order


async def list_order_items(db: AsyncSession, order_id: UUID) -> list[OrderItem]:
    return list(
        (await db.execute(select(OrderItem).where(OrderItem.order_id == order_id))).scalars().all()
    )


async def list_orders(db: AsyncSession, user_id: UUID, skip: int, limit: int) -> tuple[list[Order], int]:
    base = select(Order).where(Order.user_id == user_id)
    total = (await db.execute(select(func.count()).select_from(base.subquery()))).scalar_one()
    orders = (
        (await db.execute(base.order_by(Order.created_at.desc()).offset(skip).limit(limit))).scalars().all()
    )
    return list(orders), int(total)


async def get_order(db: AsyncSession, order_id: UUID, user_id: UUID) -> Order | None:
    return (
        await db.execute(select(Order).where(Order.id == order_id, Order.user_id == user_id))
    ).scalar_one_or_none()


async def get_order_by_no(db: AsyncSession, order_no: str, user_id: UUID) -> Order | None:
    return (
        await db.execute(
            select(Order).where(Order.order_no == order_no.strip(), Order.user_id == user_id)
        )
    ).scalar_one_or_none()


async def mark_order_paid(db: AsyncSession, order: Order) -> Order:
    order.status = "paid"
    await db.flush()
    await db.refresh(order)
    return order


async def create_ticket(
    db: AsyncSession,
    *,
    user_id: UUID,
    order_id: UUID,
    ticket_type: str,
    reason: str,
) -> AfterSalesTicket:
    ticket = AfterSalesTicket(
        ticket_no=_ticket_number(),
        user_id=user_id,
        order_id=order_id,
        type=ticket_type,
        reason=reason,
    )
    db.add(ticket)
    await db.flush()
    await db.refresh(ticket)
    return ticket


async def list_tickets(db: AsyncSession, user_id: UUID, skip: int, limit: int) -> tuple[list[AfterSalesTicket], int]:
    base = select(AfterSalesTicket).where(AfterSalesTicket.user_id == user_id)
    total = (await db.execute(select(func.count()).select_from(base.subquery()))).scalar_one()
    tickets = (
        (await db.execute(base.order_by(AfterSalesTicket.created_at.desc()).offset(skip).limit(limit)))
        .scalars()
        .all()
    )
    return list(tickets), int(total)


async def get_ticket(db: AsyncSession, ticket_id: UUID, user_id: UUID) -> AfterSalesTicket | None:
    return (
        await db.execute(
            select(AfterSalesTicket).where(
                AfterSalesTicket.id == ticket_id,
                AfterSalesTicket.user_id == user_id,
            )
        )
    ).scalar_one_or_none()


async def get_ticket_by_no(
    db: AsyncSession, ticket_no: str, user_id: UUID
) -> AfterSalesTicket | None:
    return (
        await db.execute(
            select(AfterSalesTicket).where(
                AfterSalesTicket.ticket_no == ticket_no.strip(),
                AfterSalesTicket.user_id == user_id,
            )
        )
    ).scalar_one_or_none()


async def get_ticket_for_update(db: AsyncSession, ticket_id: UUID) -> AfterSalesTicket | None:
    return (
        await db.execute(
            select(AfterSalesTicket).where(AfterSalesTicket.id == ticket_id).with_for_update()
        )
    ).scalar_one_or_none()


async def list_ticket_messages(db: AsyncSession, ticket_id: UUID) -> list[AfterSalesMessage]:
    return list(
        (
            await db.execute(
                select(AfterSalesMessage)
                .where(AfterSalesMessage.ticket_id == ticket_id)
                .order_by(AfterSalesMessage.created_at)
            )
        )
        .scalars()
        .all()
    )


async def add_ticket_message(
    db: AsyncSession,
    *,
    ticket_id: UUID,
    sender_id: UUID,
    content: str,
) -> AfterSalesMessage:
    message = AfterSalesMessage(
        ticket_id=ticket_id,
        sender_id=sender_id,
        sender_role="user",
        content=content,
    )
    db.add(message)
    await db.flush()
    await db.refresh(message)
    return message


async def create_proposal(
    db: AsyncSession,
    *,
    ticket_id: UUID,
    user_id: UUID,
    recommended_action: str,
    refund_amount: Decimal | None,
    rationale: str,
    evidence: list[dict[str, Any]],
    agent_trace_id: str | None,
) -> ActionProposal:
    proposal = ActionProposal(
        proposal_no=_proposal_number(),
        ticket_id=ticket_id,
        user_id=user_id,
        recommended_action=recommended_action,
        refund_amount=refund_amount,
        rationale=rationale,
        evidence=evidence,
        agent_trace_id=agent_trace_id,
    )
    db.add(proposal)
    await db.flush()
    await db.refresh(proposal)
    return proposal


async def get_pending_proposal_for_ticket(
    db: AsyncSession, ticket_id: UUID
) -> ActionProposal | None:
    return (
        await db.execute(
            select(ActionProposal).where(
                ActionProposal.ticket_id == ticket_id,
                ActionProposal.status == "pending",
            )
        )
    ).scalar_one_or_none()


async def get_proposal(
    db: AsyncSession, proposal_id: UUID, *, user_id: UUID | None = None
) -> ActionProposal | None:
    query = select(ActionProposal).where(ActionProposal.id == proposal_id).with_for_update()
    if user_id is not None:
        query = query.where(ActionProposal.user_id == user_id)
    return (await db.execute(query)).scalar_one_or_none()


async def list_proposals(
    db: AsyncSession,
    *,
    status: str | None,
    user_id: UUID | None,
    skip: int,
    limit: int,
) -> tuple[list[ActionProposal], int]:
    query = select(ActionProposal)
    if status:
        query = query.where(ActionProposal.status == status)
    if user_id:
        query = query.where(ActionProposal.user_id == user_id)
    total = (await db.execute(select(func.count()).select_from(query.subquery()))).scalar_one()
    proposals = (
        (
            await db.execute(
                query.order_by(ActionProposal.created_at.desc()).offset(skip).limit(limit)
            )
        )
        .scalars()
        .all()
    )
    return list(proposals), int(total)


async def decide_proposal(
    db: AsyncSession,
    proposal: ActionProposal,
    *,
    status: str,
    decided_by_id: UUID,
    decision_note: str,
) -> ActionProposal:
    proposal.status = status
    proposal.decided_by_id = decided_by_id
    proposal.decision_note = decision_note
    proposal.decided_at = datetime.now(UTC)
    await db.flush()
    await db.refresh(proposal)
    return proposal


async def create_audit_event(
    db: AsyncSession,
    *,
    actor_id: UUID | None,
    action: str,
    entity_type: str,
    entity_id: UUID | None,
    request_id: str | None,
    details: dict[str, Any],
) -> AuditEvent:
    event = AuditEvent(
        actor_id=actor_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        request_id=request_id,
        details=details,
    )
    db.add(event)
    await db.flush()
    return event


async def create_agent_run(
    db: AsyncSession,
    *,
    trace_id: str,
    request_id: str | None,
    user_id: UUID,
    conversation_id: UUID | None,
    model: str,
    prompt_version: str,
    prompt: str,
) -> AgentRun:
    run = AgentRun(
        trace_id=trace_id,
        request_id=request_id,
        user_id=user_id,
        conversation_id=conversation_id,
        model=model,
        prompt_version=prompt_version,
        prompt=prompt,
    )
    db.add(run)
    await db.flush()
    await db.refresh(run)
    return run


async def finish_agent_run(
    db: AsyncSession,
    run: AgentRun,
    *,
    status: str,
    stop_reason: str,
    input_tokens: int,
    output_tokens: int,
    total_tokens: int,
    latency_ms: int,
    error: str = "",
) -> AgentRun:
    run.status = status
    run.stop_reason = stop_reason
    run.input_tokens = input_tokens
    run.output_tokens = output_tokens
    run.total_tokens = total_tokens
    run.latency_ms = latency_ms
    run.error = error
    await db.flush()
    await db.refresh(run)
    return run


async def add_agent_step(
    db: AsyncSession,
    *,
    run_id: UUID,
    sequence: int,
    node: str,
    status: str,
    latency_ms: int,
    tool_name: str | None,
    payload: dict[str, Any],
    error: str = "",
) -> AgentStep:
    step = AgentStep(
        run_id=run_id,
        sequence=sequence,
        node=node,
        status=status,
        latency_ms=latency_ms,
        tool_name=tool_name,
        payload=payload,
        error=error,
    )
    db.add(step)
    await db.flush()
    return step


async def list_agent_runs(
    db: AsyncSession,
    *,
    user_id: UUID | None,
    skip: int,
    limit: int,
) -> tuple[list[AgentRun], int]:
    query = select(AgentRun)
    if user_id is not None:
        query = query.where(AgentRun.user_id == user_id)
    total = (await db.execute(select(func.count()).select_from(query.subquery()))).scalar_one()
    runs = (
        (
            await db.execute(
                query.order_by(AgentRun.created_at.desc()).offset(skip).limit(limit)
            )
        )
        .scalars()
        .all()
    )
    return list(runs), int(total)


async def list_agent_steps(db: AsyncSession, run_id: UUID) -> list[AgentStep]:
    return list(
        (
            await db.execute(
                select(AgentStep)
                .where(AgentStep.run_id == run_id)
                .order_by(AgentStep.sequence)
            )
        )
        .scalars()
        .all()
    )
