"""Shop service tests for ownership, stock locking, and human approval."""

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.core.exceptions import AlreadyExistsError, BadRequestError, NotFoundError
from app.schemas.shop import (
    EvidenceItem,
    OrderCreate,
    OrderItemCreate,
    ProposalCreate,
    TicketCreate,
)
from app.services.shop import ShopService


def _product(stock: int = 5) -> MagicMock:
    product = MagicMock()
    product.id = uuid4()
    product.name = "Test product"
    product.price = Decimal("99.00")
    product.stock = stock
    product.status = "on"
    return product


def _order(*, user_id=None, status: str = "paid") -> MagicMock:
    order = MagicMock()
    order.id = uuid4()
    order.order_no = "ORD-20260101000000-ABCD"
    order.user_id = user_id or uuid4()
    order.status = status
    order.total_amount = Decimal("99.00")
    return order


def _ticket(*, user_id=None, order_id=None, status: str = "pending") -> MagicMock:
    ticket = MagicMock()
    ticket.id = uuid4()
    ticket.ticket_no = "AS-20260101000000-ABCD"
    ticket.user_id = user_id or uuid4()
    ticket.order_id = order_id or uuid4()
    ticket.status = status
    ticket.type = "refund"
    ticket.reason = "Damaged item"
    ticket.refund_amount = None
    ticket.resolution = ""
    return ticket


@pytest.fixture
def service() -> ShopService:
    return ShopService(AsyncMock())


@pytest.mark.anyio
async def test_create_order_locks_products_and_deducts_stock(service: ShopService) -> None:
    product = _product()
    order = _order(status="pending")
    data = OrderCreate(items=[OrderItemCreate(product_id=product.id, quantity=2)])

    with (
        patch("app.services.shop.shop_repo") as repo,
    ):
        repo.get_product_for_update = AsyncMock(return_value=product)
        repo.create_order = AsyncMock(return_value=order)
        repo.create_audit_event = AsyncMock()

        result = await service.create_order(
            user_id=order.user_id, data=data, request_id="req-1"
        )

    assert result is order
    repo.get_product_for_update.assert_awaited_once()
    repo.create_order.assert_awaited_once()
    repo.create_audit_event.assert_awaited_once()


@pytest.mark.anyio
async def test_create_order_rejects_insufficient_stock(service: ShopService) -> None:
    product = _product(stock=1)
    data = OrderCreate(items=[OrderItemCreate(product_id=product.id, quantity=2)])

    with patch("app.services.shop.shop_repo") as repo:
        repo.get_product_for_update = AsyncMock(return_value=product)

        with pytest.raises(BadRequestError, match="Insufficient stock"):
            await service.create_order(user_id=uuid4(), data=data)


@pytest.mark.anyio
async def test_order_ownership_is_enforced(service: ShopService) -> None:
    with patch("app.services.shop.shop_repo") as repo:
        repo.get_order = AsyncMock(return_value=None)

        with pytest.raises(NotFoundError):
            await service.get_order(order_id=uuid4(), user_id=uuid4())


@pytest.mark.anyio
async def test_unpaid_order_cannot_create_ticket(service: ShopService) -> None:
    order = _order(status="pending")

    with patch("app.services.shop.shop_repo") as repo:
        repo.get_order = AsyncMock(return_value=order)
        data = TicketCreate(order_id=order.id, type="refund", reason="Damaged")

        with pytest.raises(BadRequestError, match="not eligible"):
            await service.create_ticket(user_id=order.user_id, data=data)


@pytest.mark.anyio
async def test_high_risk_proposal_requires_evidence(service: ShopService) -> None:
    order = _order()
    ticket = _ticket(user_id=order.user_id, order_id=order.id)
    data = ProposalCreate(
        ticket_id=ticket.id,
        recommended_action="approve_refund",
        refund_amount=Decimal("20.00"),
        rationale="Policy supports a refund",
        evidence=[],
    )

    with patch("app.services.shop.shop_repo") as repo:
        repo.get_ticket = AsyncMock(return_value=ticket)
        repo.get_order = AsyncMock(return_value=order)
        repo.get_pending_proposal_for_ticket = AsyncMock(return_value=None)

        with pytest.raises(BadRequestError, match="require evidence"):
            await service.create_proposal(user_id=order.user_id, data=data)


@pytest.mark.anyio
async def test_proposal_cannot_exceed_order_total(service: ShopService) -> None:
    order = _order()
    ticket = _ticket(user_id=order.user_id, order_id=order.id)
    data = ProposalCreate(
        ticket_id=ticket.id,
        recommended_action="approve_refund",
        refund_amount=Decimal("100.00"),
        rationale="Policy supports a refund",
        evidence=[EvidenceItem(source="refund-policy.md", quote="Refunds are supported")],
    )

    with patch("app.services.shop.shop_repo") as repo:
        repo.get_ticket = AsyncMock(return_value=ticket)
        repo.get_order = AsyncMock(return_value=order)
        repo.get_pending_proposal_for_ticket = AsyncMock(return_value=None)

        with pytest.raises(BadRequestError, match="cannot exceed"):
            await service.create_proposal(user_id=order.user_id, data=data)


@pytest.mark.anyio
async def test_duplicate_pending_proposal_is_rejected(service: ShopService) -> None:
    order = _order()
    ticket = _ticket(user_id=order.user_id, order_id=order.id)
    data = ProposalCreate(
        ticket_id=ticket.id,
        recommended_action="manual_review",
        rationale="Needs review",
    )

    with patch("app.services.shop.shop_repo") as repo:
        repo.get_ticket = AsyncMock(return_value=ticket)
        repo.get_order = AsyncMock(return_value=order)
        repo.get_pending_proposal_for_ticket = AsyncMock(return_value=MagicMock(id=uuid4()))

        with pytest.raises(AlreadyExistsError):
            await service.create_proposal(user_id=order.user_id, data=data)


@pytest.mark.anyio
async def test_agent_can_only_create_pending_proposal(service: ShopService) -> None:
    order = _order()
    ticket = _ticket(user_id=order.user_id, order_id=order.id)
    proposal = MagicMock()
    proposal.id = uuid4()
    proposal.proposal_no = "AP-20260101000000-ABCD"
    proposal.recommended_action = "approve_refund"
    proposal.refund_amount = Decimal("20.00")
    proposal.status = "pending"
    data = ProposalCreate(
        ticket_id=ticket.id,
        recommended_action="approve_refund",
        refund_amount=Decimal("20.00"),
        rationale="Policy supports a refund",
        evidence=[EvidenceItem(source="refund-policy.md", quote="Refunds are supported")],
    )

    with patch("app.services.shop.shop_repo") as repo:
        repo.get_ticket = AsyncMock(return_value=ticket)
        repo.get_order = AsyncMock(return_value=order)
        repo.get_pending_proposal_for_ticket = AsyncMock(return_value=None)
        repo.create_proposal = AsyncMock(return_value=proposal)
        repo.create_audit_event = AsyncMock()

        result = await service.create_proposal(
            user_id=order.user_id, data=data, request_id="req-proposal"
        )

    assert result.status == "pending"
    assert ticket.status == "waiting_approval"
    repo.create_audit_event.assert_awaited_once()


@pytest.mark.anyio
async def test_human_approval_executes_deterministic_state_change(service: ShopService) -> None:
    user_id = uuid4()
    admin_id = uuid4()
    order = _order(user_id=user_id, status="paid")
    ticket = _ticket(user_id=user_id, order_id=order.id, status="waiting_approval")
    proposal = MagicMock()
    proposal.id = uuid4()
    proposal.proposal_no = "AP-20260101000000-ABCD"
    proposal.ticket_id = ticket.id
    proposal.status = "pending"
    proposal.refund_amount = Decimal("20.00")
    proposal.rationale = "Policy supports a refund"
    proposal.recommended_action = "approve_refund"

    with patch("app.services.shop.shop_repo") as repo:
        repo.get_proposal = AsyncMock(return_value=proposal)
        repo.get_ticket_for_update = AsyncMock(return_value=ticket)
        repo.get_order = AsyncMock(return_value=order)
        repo.decide_proposal = AsyncMock(
            side_effect=lambda db, item, **kwargs: _mark_decided(item, kwargs)
        )
        repo.create_audit_event = AsyncMock()

        result = await service.decide_proposal(
            proposal_id=proposal.id,
            admin_id=admin_id,
            decision="approve",
            note="Reviewed supporting evidence",
            request_id="req-approve",
        )

    assert result.status == "approved"
    assert ticket.status == "approved"
    assert ticket.refund_amount == Decimal("20.00")
    assert order.status == "refund_pending"
    repo.create_audit_event.assert_awaited_once()


def _mark_decided(proposal: MagicMock, kwargs: dict) -> MagicMock:
    proposal.status = kwargs["status"]
    proposal.decided_by_id = kwargs["decided_by_id"]
    proposal.decision_note = kwargs["decision_note"]
    return proposal
