"""Permission-scoped commerce tools used by the after-sales agent."""

import asyncio
import json
import logging
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID

from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool

from app.agents.tools.rag_tool import search_knowledge_base
from app.db.session import get_db_context
from app.repositories import shop as shop_repo
from app.schemas.shop import EvidenceItem, ProposalCreate
from app.services.shop import ShopService

logger = logging.getLogger(__name__)

POLICY_COLLECTION = "after_sales_policies"
TOOL_TIMEOUT_SECONDS = 12
MAX_TOOL_RESULT_CHARS = 12_000


def _tool_error(code: str, message: str) -> str:
    return json.dumps({"ok": False, "error": {"code": code, "message": message}}, ensure_ascii=False)


def _json(payload: dict[str, Any]) -> str:
    text = json.dumps(payload, ensure_ascii=False, default=str)
    if len(text) <= MAX_TOOL_RESULT_CHARS:
        return text
    return json.dumps(
        {
            "ok": payload.get("ok", True),
            "truncated": True,
            "preview": text[:MAX_TOOL_RESULT_CHARS],
        },
        ensure_ascii=False,
    )


def _user_id(config: RunnableConfig) -> UUID:
    value = (config.get("configurable") or {}).get("user_id")
    if not value:
        raise ValueError("Authenticated user context is missing")
    return UUID(str(value))


def _trace_id(config: RunnableConfig) -> str | None:
    value = (config.get("configurable") or {}).get("trace_id")
    return str(value) if value else None


def _request_id(config: RunnableConfig) -> str | None:
    value = (config.get("configurable") or {}).get("request_id")
    return str(value) if value else _trace_id(config)


async def _with_timeout(awaitable: Any) -> Any:
    return await asyncio.wait_for(awaitable, timeout=TOOL_TIMEOUT_SECONDS)


@tool
async def get_order(order_no: str, config: RunnableConfig) -> str:
    """Look up one order owned by the current customer.

    Args:
        order_no: The customer-visible order number, for example ORD-...
    """

    async def execute() -> str:
        user_id = _user_id(config)
        async with get_db_context() as db:
            order = await shop_repo.get_order_by_no(db, order_no, user_id)
            if order is None:
                return _tool_error("ORDER_NOT_FOUND", "No matching order belongs to this customer")
            items = await shop_repo.list_order_items(db, order.id)
            return _json(
                {
                    "ok": True,
                    "order": {
                        "order_no": order.order_no,
                        "status": order.status,
                        "total_amount": str(order.total_amount),
                        "created_at": order.created_at,
                        "items": [
                            {
                                "product_name": item.product_name,
                                "quantity": item.quantity,
                                "price": str(item.price),
                            }
                            for item in items
                        ],
                    },
                }
            )

    try:
        return await _with_timeout(execute())
    except TimeoutError:
        return _tool_error("TOOL_TIMEOUT", "Order lookup timed out")
    except Exception as exc:
        logger.exception("get_order tool failed")
        return _tool_error("TOOL_FAILED", str(exc))


@tool
async def get_logistics(order_no: str, config: RunnableConfig) -> str:
    """Read the logistics milestones for an order owned by the current customer.

    This demo uses deterministic simulated milestones because no carrier API is
    configured. The response always identifies the data as simulated.
    """

    async def execute() -> str:
        user_id = _user_id(config)
        async with get_db_context() as db:
            order = await shop_repo.get_order_by_no(db, order_no, user_id)
            if order is None:
                return _tool_error("ORDER_NOT_FOUND", "No matching order belongs to this customer")

            now = datetime.now(UTC)
            milestones: list[dict[str, Any]] = []
            if order.status in {"paid", "shipped", "completed", "refund_pending"}:
                milestones.append(
                    {
                        "at": min(order.created_at + timedelta(hours=1), now),
                        "status": "carrier_accepted",
                        "description": "Carrier accepted the parcel",
                    }
                )
            if order.status in {"shipped", "completed", "refund_pending"}:
                milestones.append(
                    {
                        "at": min(order.created_at + timedelta(days=1), now),
                        "status": "in_transit",
                        "description": "Parcel is in transit",
                    }
                )
            if order.status == "completed":
                milestones.append(
                    {
                        "at": min(order.created_at + timedelta(days=3), now),
                        "status": "delivered",
                        "description": "Parcel delivered",
                    }
                )
            return _json(
                {
                    "ok": True,
                    "source": "simulated",
                    "order_no": order.order_no,
                    "order_status": order.status,
                    "milestones": milestones,
                }
            )

    try:
        return await _with_timeout(execute())
    except TimeoutError:
        return _tool_error("TOOL_TIMEOUT", "Logistics lookup timed out")
    except Exception as exc:
        logger.exception("get_logistics tool failed")
        return _tool_error("TOOL_FAILED", str(exc))


@tool
async def get_after_sales_ticket(ticket_no: str, config: RunnableConfig) -> str:
    """Read an after-sales ticket and its conversation, scoped to the customer."""

    async def execute() -> str:
        user_id = _user_id(config)
        async with get_db_context() as db:
            ticket = await shop_repo.get_ticket_by_no(db, ticket_no, user_id)
            if ticket is None:
                return _tool_error("TICKET_NOT_FOUND", "No matching ticket belongs to this customer")
            messages = await shop_repo.list_ticket_messages(db, ticket.id)
            return _json(
                {
                    "ok": True,
                    "ticket": {
                        "ticket_no": ticket.ticket_no,
                        "type": ticket.type,
                        "status": ticket.status,
                        "reason": ticket.reason,
                        "refund_amount": ticket.refund_amount,
                        "resolution": ticket.resolution,
                        "messages": [
                            {
                                "role": message.sender_role,
                                "content": message.content,
                                "created_at": message.created_at,
                            }
                            for message in messages
                        ],
                    },
                }
            )

    try:
        return await _with_timeout(execute())
    except TimeoutError:
        return _tool_error("TOOL_TIMEOUT", "Ticket lookup timed out")
    except Exception as exc:
        logger.exception("get_after_sales_ticket tool failed")
        return _tool_error("TOOL_FAILED", str(exc))


@tool
async def check_refund_eligibility(order_no: str, config: RunnableConfig) -> str:
    """Evaluate deterministic order-level constraints for a refund.

    This does not approve a refund. It reports objective eligibility signals so
    the agent can combine them with retrieved policy evidence.
    """

    async def execute() -> str:
        user_id = _user_id(config)
        async with get_db_context() as db:
            order = await shop_repo.get_order_by_no(db, order_no, user_id)
            if order is None:
                return _tool_error("ORDER_NOT_FOUND", "No matching order belongs to this customer")
            eligible_status = order.status in {"paid", "shipped", "completed"}
            return _json(
                {
                    "ok": True,
                    "order_no": order.order_no,
                    "order_status": order.status,
                    "preliminary_eligible": eligible_status,
                    "refundable_amount": str(order.total_amount) if eligible_status else "0.00",
                    "missing_checks": [
                        "policy_reason",
                        "item_condition",
                    ],
                    "note": "This is a constraint check, not a final business decision.",
                }
            )

    try:
        return await _with_timeout(execute())
    except TimeoutError:
        return _tool_error("TOOL_TIMEOUT", "Refund eligibility check timed out")
    except Exception as exc:
        logger.exception("check_refund_eligibility tool failed")
        return _tool_error("TOOL_FAILED", str(exc))


@tool
async def search_after_sales_policy(query: str, top_k: int = 5) -> str:
    """Search the versioned after-sales policy collection with hybrid retrieval.

    Every returned result includes a source filename and chunk metadata. Cite
    the source labels in the final answer.
    """
    try:
        return await asyncio.wait_for(
            search_knowledge_base(
                query=query,
                collection=POLICY_COLLECTION,
                top_k=max(1, min(top_k, 8)),
            ),
            timeout=TOOL_TIMEOUT_SECONDS,
        )
    except TimeoutError:
        return _tool_error("TOOL_TIMEOUT", "Policy search timed out")
    except Exception as exc:
        logger.exception("search_after_sales_policy tool failed")
        return _tool_error("TOOL_FAILED", str(exc))


@tool
async def create_refund_proposal(
    ticket_no: str,
    recommended_action: str,
    refund_amount: str,
    rationale: str,
    evidence: list[dict[str, str]],
    config: RunnableConfig,
) -> str:
    """Create a high-risk proposal for human approval. This does not execute a refund.

    Args:
        ticket_no: Customer-visible after-sales ticket number.
        recommended_action: approve_refund, approve_return, exchange, reject, or manual_review.
        refund_amount: Decimal amount as a string. Use 0 when no refund is proposed.
        rationale: Concise evidence-based recommendation.
        evidence: Sources used, each with source and quote keys.
    """

    async def execute() -> str:
        user_id = _user_id(config)
        async with get_db_context() as db:
            ticket = await shop_repo.get_ticket_by_no(db, ticket_no, user_id)
            if ticket is None:
                return _tool_error("TICKET_NOT_FOUND", "No matching ticket belongs to this customer")
            amount = Decimal(refund_amount) if refund_amount else None
            if amount is not None and amount <= 0:
                amount = None
            service = ShopService(db)
            proposal = await service.create_proposal(
                user_id=user_id,
                data=ProposalCreate(
                    ticket_id=ticket.id,
                    recommended_action=recommended_action,
                    refund_amount=amount,
                    rationale=rationale,
                    evidence=[EvidenceItem(**item) for item in evidence],
                    agent_trace_id=_trace_id(config),
                ),
                request_id=_request_id(config),
            )
            return _json(
                {
                    "ok": True,
                    "proposal_no": proposal.proposal_no,
                    "status": proposal.status,
                    "message": "Proposal created. A human reviewer must approve it.",
                }
            )

    try:
        return await _with_timeout(execute())
    except TimeoutError:
        return _tool_error("TOOL_TIMEOUT", "Proposal creation timed out")
    except Exception as exc:
        logger.exception("create_refund_proposal tool failed")
        return _tool_error("TOOL_FAILED", str(exc))


SHOP_TOOLS = [
    get_order,
    get_logistics,
    get_after_sales_ticket,
    check_refund_eligibility,
    search_after_sales_policy,
    create_refund_proposal,
]

READ_ONLY_SHOP_TOOLS = [
    get_order,
    get_logistics,
    get_after_sales_ticket,
    check_refund_eligibility,
    search_after_sales_policy,
]
