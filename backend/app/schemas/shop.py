"""ShopAgent commerce and after-sales schemas."""

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import Field

from app.schemas.base import BaseSchema, TimestampSchema


class ProductCreate(BaseSchema):
    name: str = Field(min_length=1, max_length=255)
    description: str = ""
    price: Decimal = Field(gt=0)
    stock: int = Field(default=0, ge=0)


class ProductRead(ProductCreate, TimestampSchema):
    id: UUID
    status: str


class ProductList(BaseSchema):
    items: list[ProductRead]
    total: int


class OrderItemCreate(BaseSchema):
    product_id: UUID
    quantity: int = Field(ge=1, le=99)


class OrderCreate(BaseSchema):
    items: list[OrderItemCreate] = Field(min_length=1)


class OrderItemRead(BaseSchema):
    id: UUID
    product_id: UUID
    product_name: str
    price: Decimal
    quantity: int


class OrderRead(TimestampSchema):
    id: UUID
    order_no: str
    user_id: UUID
    status: str
    total_amount: Decimal
    items: list[OrderItemRead]


class OrderList(BaseSchema):
    items: list[OrderRead]
    total: int


class TicketCreate(BaseSchema):
    order_id: UUID
    type: str = Field(default="refund", pattern=r"^(refund|return|exchange|damage|logistics|other)$")
    reason: str = Field(default="", max_length=10_000)


class TicketMessageCreate(BaseSchema):
    content: str = Field(min_length=1, max_length=10_000)


class TicketMessageRead(BaseSchema):
    id: UUID
    sender_id: UUID | None
    sender_role: str
    content: str


class TicketRead(TimestampSchema):
    id: UUID
    ticket_no: str
    user_id: UUID
    order_id: UUID
    type: str
    reason: str
    status: str
    refund_amount: Decimal | None
    resolution: str
    messages: list[TicketMessageRead]


class TicketList(BaseSchema):
    items: list[TicketRead]
    total: int


class EvidenceItem(BaseSchema):
    source: str = Field(min_length=1, max_length=255)
    quote: str = Field(min_length=1, max_length=2_000)
    score: float | None = Field(default=None, ge=0, le=1)


class ProposalCreate(BaseSchema):
    ticket_id: UUID
    recommended_action: str = Field(
        pattern=r"^(approve_refund|approve_return|exchange|reject|manual_review)$"
    )
    refund_amount: Decimal | None = Field(default=None, gt=0)
    rationale: str = Field(min_length=1, max_length=10_000)
    evidence: list[EvidenceItem] = Field(default_factory=list, max_length=20)
    agent_trace_id: str | None = Field(default=None, max_length=100)


class ProposalDecision(BaseSchema):
    decision: str = Field(pattern=r"^(approve|reject)$")
    note: str = Field(default="", max_length=10_000)


class ProposalRead(BaseSchema, TimestampSchema):
    id: UUID
    proposal_no: str
    ticket_id: UUID
    user_id: UUID
    recommended_action: str
    refund_amount: Decimal | None
    rationale: str
    evidence: list[dict[str, Any]]
    status: str
    agent_trace_id: str | None
    decided_by_id: UUID | None
    decision_note: str
    decided_at: datetime | None


class ProposalList(BaseSchema):
    items: list[ProposalRead]
    total: int


class AgentStepRead(BaseSchema):
    id: UUID
    sequence: int
    node: str
    status: str
    latency_ms: int
    tool_name: str | None
    payload: dict[str, Any]
    error: str
    created_at: datetime


class AgentRunRead(BaseSchema, TimestampSchema):
    id: UUID
    trace_id: str
    request_id: str | None
    user_id: UUID
    conversation_id: UUID | None
    model: str
    prompt_version: str
    status: str
    stop_reason: str | None
    input_tokens: int
    output_tokens: int
    total_tokens: int
    latency_ms: int
    error: str
    steps: list[AgentStepRead] = Field(default_factory=list)


class AgentRunList(BaseSchema):
    items: list[AgentRunRead]
    total: int
