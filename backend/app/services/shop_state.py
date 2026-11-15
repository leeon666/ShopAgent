"""Explicit state machines for ShopAgent's order and after-sales workflows."""

from collections.abc import Mapping

from app.core.exceptions import BadRequestError

ORDER_TRANSITIONS: Mapping[str, frozenset[str]] = {
    "pending": frozenset({"paid", "cancelled"}),
    "paid": frozenset({"shipped", "refund_pending", "cancelled"}),
    "shipped": frozenset({"completed", "refund_pending"}),
    "completed": frozenset({"refund_pending"}),
    "refund_pending": frozenset({"refunded", "paid", "shipped", "completed"}),
    "refunded": frozenset(),
    "cancelled": frozenset(),
}

TICKET_TRANSITIONS: Mapping[str, frozenset[str]] = {
    "pending": frozenset({"agent_review", "waiting_customer", "waiting_approval", "cancelled"}),
    "agent_review": frozenset({"waiting_customer", "waiting_approval", "resolved", "cancelled"}),
    "waiting_customer": frozenset({"agent_review", "waiting_approval", "cancelled"}),
    "waiting_approval": frozenset({"approved", "rejected", "cancelled"}),
    "approved": frozenset({"resolved"}),
    "rejected": frozenset({"agent_review"}),
    "resolved": frozenset(),
    "cancelled": frozenset(),
}


def transition(
    *,
    entity: str,
    current: str,
    target: str,
    transitions: Mapping[str, frozenset[str]],
) -> str:
    """Validate and return a target state or raise a domain error."""
    allowed = transitions.get(current, frozenset())
    if target not in allowed:
        raise BadRequestError(
            message=f"Invalid {entity} state transition: {current} -> {target}",
            details={"current": current, "target": target, "allowed": sorted(allowed)},
        )
    return target


def transition_order(current: str, target: str) -> str:
    return transition(
        entity="order",
        current=current,
        target=target,
        transitions=ORDER_TRANSITIONS,
    )


def transition_ticket(current: str, target: str) -> str:
    return transition(
        entity="after-sales ticket",
        current=current,
        target=target,
        transitions=TICKET_TRANSITIONS,
    )
