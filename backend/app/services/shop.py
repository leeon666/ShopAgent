"""ShopAgent business services."""

from collections import defaultdict
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AlreadyExistsError, BadRequestError, NotFoundError
from app.db.models.shop import (
    ActionProposal,
    AfterSalesMessage,
    AfterSalesTicket,
    AgentRun,
    AgentStep,
    Order,
    OrderItem,
    Product,
)
from app.repositories import shop as shop_repo
from app.schemas.shop import OrderCreate, ProductCreate, ProposalCreate, TicketCreate
from app.services.shop_state import transition_order, transition_ticket


class ShopService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_products(self, *, skip: int, limit: int) -> tuple[list[Product], int]:
        return await shop_repo.list_products(self.db, skip, limit)

    async def create_product(self, data: ProductCreate) -> Product:
        return await shop_repo.create_product(
            self.db,
            name=data.name,
            description=data.description,
            price=data.price,
            stock=data.stock,
        )

    async def create_order(
        self, *, user_id: UUID, data: OrderCreate, request_id: str | None = None
    ) -> Order:
        quantities: dict[UUID, int] = defaultdict(int)
        for item in data.items:
            quantities[item.product_id] += item.quantity
        resolved: list[tuple[Product, int]] = []
        # Lock product rows in UUID order to prevent overselling and reduce
        # deadlock risk between concurrent order requests.
        for product_id in sorted(quantities, key=str):
            quantity = quantities[product_id]
            product = await shop_repo.get_product_for_update(self.db, product_id)
            if product is None or product.status != "on":
                raise NotFoundError(message="Product not found or unavailable")
            if product.stock < quantity:
                raise BadRequestError(
                    message=f"Insufficient stock for {product.name}",
                    details={"available": product.stock, "requested": quantity},
                )
            resolved.append((product, quantity))
        order = await shop_repo.create_order(self.db, user_id=user_id, items=resolved)
        await self._audit(
            actor_id=user_id,
            action="order.created",
            entity_type="order",
            entity_id=order.id,
            request_id=request_id,
            details={"order_no": order.order_no, "total_amount": str(order.total_amount)},
        )
        return order

    async def list_orders(self, *, user_id: UUID, skip: int, limit: int) -> tuple[list[Order], int]:
        return await shop_repo.list_orders(self.db, user_id, skip, limit)

    async def get_order(self, *, order_id: UUID, user_id: UUID) -> Order:
        order = await shop_repo.get_order(self.db, order_id, user_id)
        if order is None:
            raise NotFoundError(message="Order not found")
        return order

    async def mark_paid(
        self, *, order_id: UUID, user_id: UUID, request_id: str | None = None
    ) -> Order:
        order = await self.get_order(order_id=order_id, user_id=user_id)
        transition_order(order.status, "paid")
        order = await shop_repo.mark_order_paid(self.db, order)
        await self._audit(
            actor_id=user_id,
            action="order.paid",
            entity_type="order",
            entity_id=order.id,
            request_id=request_id,
            details={"order_no": order.order_no, "mode": "simulated"},
        )
        return order

    async def order_items(self, order: Order) -> list[OrderItem]:
        return await shop_repo.list_order_items(self.db, order.id)

    async def create_ticket(
        self, *, user_id: UUID, data: TicketCreate, request_id: str | None = None
    ) -> AfterSalesTicket:
        order = await self.get_order(order_id=data.order_id, user_id=user_id)
        if order.status not in {"paid", "shipped", "completed"}:
            raise BadRequestError(message="Order is not eligible for after-sales service")
        ticket = await shop_repo.create_ticket(
            self.db,
            user_id=user_id,
            order_id=order.id,
            ticket_type=data.type,
            reason=data.reason,
        )
        await self._audit(
            actor_id=user_id,
            action="after_sales.created",
            entity_type="after_sales_ticket",
            entity_id=ticket.id,
            request_id=request_id,
            details={"ticket_no": ticket.ticket_no, "type": ticket.type},
        )
        return ticket

    async def list_tickets(
        self, *, user_id: UUID, skip: int, limit: int
    ) -> tuple[list[AfterSalesTicket], int]:
        return await shop_repo.list_tickets(self.db, user_id, skip, limit)

    async def get_ticket(self, *, ticket_id: UUID, user_id: UUID) -> AfterSalesTicket:
        ticket = await shop_repo.get_ticket(self.db, ticket_id, user_id)
        if ticket is None:
            raise NotFoundError(message="After-sales ticket not found")
        return ticket

    async def ticket_messages(self, ticket_id: UUID) -> list[AfterSalesMessage]:
        return await shop_repo.list_ticket_messages(self.db, ticket_id)

    async def add_ticket_message(
        self,
        *,
        ticket_id: UUID,
        user_id: UUID,
        content: str,
        request_id: str | None = None,
    ) -> AfterSalesMessage:
        ticket = await self.get_ticket(ticket_id=ticket_id, user_id=user_id)
        if ticket.status in {"rejected", "completed", "cancelled"}:
            raise BadRequestError(message="Ticket is already closed")
        message = await shop_repo.add_ticket_message(
            self.db,
            ticket_id=ticket.id,
            sender_id=user_id,
            content=content,
        )
        await self._audit(
            actor_id=user_id,
            action="after_sales.message_added",
            entity_type="after_sales_ticket",
            entity_id=ticket.id,
            request_id=request_id,
            details={"message_id": str(message.id)},
        )
        return message

    async def create_proposal(
        self,
        *,
        user_id: UUID,
        data: ProposalCreate,
        request_id: str | None = None,
    ) -> ActionProposal:
        ticket = await self.get_ticket(ticket_id=data.ticket_id, user_id=user_id)
        order = await self.get_order(order_id=ticket.order_id, user_id=user_id)
        pending = await shop_repo.get_pending_proposal_for_ticket(self.db, ticket.id)
        if pending is not None:
            raise AlreadyExistsError(
                message="This ticket already has a pending approval proposal",
                details={"proposal_id": str(pending.id)},
            )
        if data.refund_amount is not None and data.refund_amount > order.total_amount:
            raise BadRequestError(
                message="Refund amount cannot exceed the order total",
                details={
                    "refund_amount": str(data.refund_amount),
                    "order_total": str(order.total_amount),
                },
            )
        if data.recommended_action in {"approve_refund", "approve_return"} and not data.evidence:
            raise BadRequestError(message="High-risk proposals require evidence")

        ticket.status = transition_ticket(ticket.status, "waiting_approval")
        proposal = await shop_repo.create_proposal(
            self.db,
            ticket_id=ticket.id,
            user_id=user_id,
            recommended_action=data.recommended_action,
            refund_amount=data.refund_amount,
            rationale=data.rationale,
            evidence=[item.model_dump(mode="json") for item in data.evidence],
            agent_trace_id=data.agent_trace_id,
        )
        await self._audit(
            actor_id=user_id,
            action="proposal.created",
            entity_type="action_proposal",
            entity_id=proposal.id,
            request_id=request_id,
            details={
                "proposal_no": proposal.proposal_no,
                "ticket_id": str(ticket.id),
                "recommended_action": proposal.recommended_action,
                "refund_amount": (
                    str(proposal.refund_amount) if proposal.refund_amount is not None else None
                ),
            },
        )
        return proposal

    async def list_proposals(
        self,
        *,
        status: str | None,
        user_id: UUID | None,
        skip: int,
        limit: int,
    ) -> tuple[list[ActionProposal], int]:
        return await shop_repo.list_proposals(
            self.db, status=status, user_id=user_id, skip=skip, limit=limit
        )

    async def get_proposal(self, *, proposal_id: UUID, user_id: UUID) -> ActionProposal:
        proposal = await shop_repo.get_proposal(self.db, proposal_id, user_id=user_id)
        if proposal is None:
            raise NotFoundError(message="Action proposal not found")
        return proposal

    async def decide_proposal(
        self,
        *,
        proposal_id: UUID,
        admin_id: UUID,
        decision: str,
        note: str,
        request_id: str | None = None,
    ) -> ActionProposal:
        proposal = await shop_repo.get_proposal(self.db, proposal_id)
        if proposal is None:
            raise NotFoundError(message="Action proposal not found")
        if proposal.status != "pending":
            raise BadRequestError(message="Only pending proposals can be decided")

        ticket = await shop_repo.get_ticket_for_update(self.db, proposal.ticket_id)
        if ticket is None:
            raise NotFoundError(message="After-sales ticket not found")
        target = "approved" if decision == "approve" else "rejected"
        ticket.status = transition_ticket(ticket.status, target)

        if decision == "approve":
            ticket.refund_amount = proposal.refund_amount
            ticket.resolution = proposal.rationale
            if proposal.recommended_action == "approve_refund":
                order = await self.get_order(order_id=ticket.order_id, user_id=ticket.user_id)
                transition_order(order.status, "refund_pending")
                order.status = "refund_pending"
            elif proposal.recommended_action == "approve_return":
                ticket.status = transition_ticket(ticket.status, "resolved")
                ticket.resolution = (
                    proposal.rationale + " Return approved; waiting for physical return."
                )
        else:
            ticket.resolution = note or "Human reviewer rejected the proposed action"

        status = "approved" if decision == "approve" else "rejected"
        proposal = await shop_repo.decide_proposal(
            self.db,
            proposal,
            status=status,
            decided_by_id=admin_id,
            decision_note=note,
        )
        await self._audit(
            actor_id=admin_id,
            action=f"proposal.{status}",
            entity_type="action_proposal",
            entity_id=proposal.id,
            request_id=request_id,
            details={
                "proposal_no": proposal.proposal_no,
                "ticket_id": str(ticket.id),
                "note": note,
                "decided_at": datetime.now(UTC).isoformat(),
            },
        )
        return proposal

    async def list_agent_runs(
        self,
        *,
        user_id: UUID | None,
        skip: int,
        limit: int,
    ) -> tuple[list[AgentRun], int]:
        return await shop_repo.list_agent_runs(
            self.db, user_id=user_id, skip=skip, limit=limit
        )

    async def agent_steps(self, run_id: UUID) -> list[AgentStep]:
        return await shop_repo.list_agent_steps(self.db, run_id)

    async def _audit(
        self,
        *,
        actor_id: UUID | None,
        action: str,
        entity_type: str,
        entity_id: UUID | None,
        request_id: str | None,
        details: dict[str, object],
    ) -> None:
        await shop_repo.create_audit_event(
            self.db,
            actor_id=actor_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            request_id=request_id,
            details=details,
        )

    @staticmethod
    def total_for(items: list[OrderItem]) -> Decimal:
        return sum((item.price * item.quantity for item in items), Decimal("0"))
