"""ShopAgent commerce and after-sales API."""

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status

from app.api.deps import CurrentAdmin, CurrentUser, DBSession
from app.db.models.shop import ActionProposal, AfterSalesTicket, AgentRun, Order
from app.schemas.shop import (
    AgentRunList,
    AgentRunRead,
    OrderCreate,
    OrderList,
    OrderRead,
    ProductCreate,
    ProductList,
    ProductRead,
    ProposalDecision,
    ProposalList,
    ProposalRead,
    TicketCreate,
    TicketList,
    TicketMessageCreate,
    TicketMessageRead,
    TicketRead,
)
from app.services.shop import ShopService

router = APIRouter()


def get_shop_service(db: DBSession) -> ShopService:
    return ShopService(db)


ShopSvc = Annotated[ShopService, Depends(get_shop_service)]


def _request_id(request: Request) -> str | None:
    request_id = getattr(request.state, "request_id", None)
    if request_id:
        return str(request_id)
    return request.headers.get("X-Request-ID")


async def _order_payload(service: ShopService, order: Order) -> dict[str, Any]:
    items = await service.order_items(order)
    return {
        "id": order.id,
        "order_no": order.order_no,
        "user_id": order.user_id,
        "status": order.status,
        "total_amount": order.total_amount,
        "created_at": order.created_at,
        "updated_at": order.updated_at,
        "items": items,
    }


async def _ticket_payload(service: ShopService, ticket: AfterSalesTicket) -> dict[str, Any]:
    messages = await service.ticket_messages(ticket.id)
    return {
        "id": ticket.id,
        "ticket_no": ticket.ticket_no,
        "user_id": ticket.user_id,
        "order_id": ticket.order_id,
        "type": ticket.type,
        "reason": ticket.reason,
        "status": ticket.status,
        "refund_amount": ticket.refund_amount,
        "resolution": ticket.resolution,
        "created_at": ticket.created_at,
        "updated_at": ticket.updated_at,
        "messages": messages,
    }


async def _run_payload(service: ShopService, run: AgentRun) -> dict[str, Any]:
    steps = await service.agent_steps(run.id)
    return {
        "id": run.id,
        "trace_id": run.trace_id,
        "request_id": run.request_id,
        "user_id": run.user_id,
        "conversation_id": run.conversation_id,
        "model": run.model,
        "prompt_version": run.prompt_version,
        "status": run.status,
        "stop_reason": run.stop_reason,
        "input_tokens": run.input_tokens,
        "output_tokens": run.output_tokens,
        "total_tokens": run.total_tokens,
        "latency_ms": run.latency_ms,
        "error": run.error,
        "created_at": run.created_at,
        "updated_at": run.updated_at,
        "steps": steps,
    }


@router.get("/products", response_model=ProductList)
async def list_products(
    service: ShopSvc,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
) -> Any:
    products, total = await service.list_products(skip=skip, limit=limit)
    return ProductList(items=[ProductRead.model_validate(product) for product in products], total=total)


@router.post("/products", response_model=ProductRead, status_code=status.HTTP_201_CREATED)
async def create_product(data: ProductCreate, service: ShopSvc, admin: CurrentAdmin) -> Any:
    return ProductRead.model_validate(await service.create_product(data))


@router.get("/orders", response_model=OrderList)
async def list_orders(
    service: ShopSvc,
    user: CurrentUser,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
) -> Any:
    orders, total = await service.list_orders(user_id=user.id, skip=skip, limit=limit)
    return OrderList(
        items=[OrderRead.model_validate(await _order_payload(service, order)) for order in orders],
        total=total,
    )


@router.post("/orders", response_model=OrderRead, status_code=status.HTTP_201_CREATED)
async def create_order(
    data: OrderCreate, service: ShopSvc, user: CurrentUser, request: Request
) -> Any:
    order = await service.create_order(
        user_id=user.id, data=data, request_id=_request_id(request)
    )
    return OrderRead.model_validate(await _order_payload(service, order))


@router.get("/orders/{order_id}", response_model=OrderRead)
async def get_order(order_id: UUID, service: ShopSvc, user: CurrentUser) -> Any:
    order = await service.get_order(order_id=order_id, user_id=user.id)
    return OrderRead.model_validate(await _order_payload(service, order))


@router.post("/orders/{order_id}/pay", response_model=OrderRead)
async def pay_order(
    order_id: UUID, service: ShopSvc, user: CurrentUser, request: Request
) -> Any:
    order = await service.mark_paid(
        order_id=order_id, user_id=user.id, request_id=_request_id(request)
    )
    return OrderRead.model_validate(await _order_payload(service, order))


@router.get("/after-sales", response_model=TicketList)
async def list_tickets(
    service: ShopSvc,
    user: CurrentUser,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
) -> Any:
    tickets, total = await service.list_tickets(user_id=user.id, skip=skip, limit=limit)
    return TicketList(
        items=[TicketRead.model_validate(await _ticket_payload(service, ticket)) for ticket in tickets],
        total=total,
    )


@router.post("/after-sales", response_model=TicketRead, status_code=status.HTTP_201_CREATED)
async def create_ticket(
    data: TicketCreate, service: ShopSvc, user: CurrentUser, request: Request
) -> Any:
    ticket = await service.create_ticket(
        user_id=user.id, data=data, request_id=_request_id(request)
    )
    return TicketRead.model_validate(await _ticket_payload(service, ticket))


@router.get("/after-sales/{ticket_id}", response_model=TicketRead)
async def get_ticket(ticket_id: UUID, service: ShopSvc, user: CurrentUser) -> Any:
    ticket = await service.get_ticket(ticket_id=ticket_id, user_id=user.id)
    return TicketRead.model_validate(await _ticket_payload(service, ticket))


@router.post("/after-sales/{ticket_id}/messages", response_model=TicketMessageRead)
async def add_ticket_message(
    ticket_id: UUID,
    data: TicketMessageCreate,
    service: ShopSvc,
    user: CurrentUser,
    request: Request,
) -> Any:
    message = await service.add_ticket_message(
        ticket_id=ticket_id,
        user_id=user.id,
        content=data.content,
        request_id=_request_id(request),
    )
    return TicketMessageRead.model_validate(message)


@router.get("/proposals", response_model=ProposalList)
async def list_my_proposals(
    service: ShopSvc,
    user: CurrentUser,
    proposal_status: str | None = Query(default=None, alias="status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
) -> Any:
    proposals, total = await service.list_proposals(
        status=proposal_status,
        user_id=user.id,
        skip=skip,
        limit=limit,
    )
    return ProposalList(
        items=[ProposalRead.model_validate(proposal) for proposal in proposals],
        total=total,
    )


@router.get("/proposals/{proposal_id}", response_model=ProposalRead)
async def get_my_proposal(
    proposal_id: UUID, service: ShopSvc, user: CurrentUser
) -> ActionProposal:
    return await service.get_proposal(proposal_id=proposal_id, user_id=user.id)


@router.get("/admin/proposals", response_model=ProposalList)
async def list_proposals_for_review(
    service: ShopSvc,
    admin: CurrentAdmin,
    proposal_status: str | None = Query(default="pending", alias="status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
) -> Any:
    proposals, total = await service.list_proposals(
        status=proposal_status,
        user_id=None,
        skip=skip,
        limit=limit,
    )
    return ProposalList(
        items=[ProposalRead.model_validate(proposal) for proposal in proposals],
        total=total,
    )


@router.post("/admin/proposals/{proposal_id}/decision", response_model=ProposalRead)
async def decide_proposal(
    proposal_id: UUID,
    data: ProposalDecision,
    service: ShopSvc,
    admin: CurrentAdmin,
    request: Request,
) -> ActionProposal:
    return await service.decide_proposal(
        proposal_id=proposal_id,
        admin_id=admin.id,
        decision=data.decision,
        note=data.note,
        request_id=_request_id(request),
    )


@router.get("/runs", response_model=AgentRunList)
async def list_my_agent_runs(
    service: ShopSvc,
    user: CurrentUser,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
) -> Any:
    runs, total = await service.list_agent_runs(user_id=user.id, skip=skip, limit=limit)
    return AgentRunList(
        items=[AgentRunRead.model_validate(await _run_payload(service, run)) for run in runs],
        total=total,
    )


@router.get("/admin/runs", response_model=AgentRunList)
async def list_agent_runs_for_admin(
    service: ShopSvc,
    admin: CurrentAdmin,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
) -> Any:
    runs, total = await service.list_agent_runs(user_id=None, skip=skip, limit=limit)
    return AgentRunList(
        items=[AgentRunRead.model_validate(await _run_payload(service, run)) for run in runs],
        total=total,
    )
