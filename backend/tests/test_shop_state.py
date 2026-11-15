"""State-machine tests for ShopAgent's order and ticket invariants."""

import pytest

from app.core.exceptions import BadRequestError
from app.services.shop_state import transition_order, transition_ticket


def test_order_happy_path() -> None:
    assert transition_order("pending", "paid") == "paid"
    assert transition_order("paid", "shipped") == "shipped"
    assert transition_order("shipped", "completed") == "completed"
    assert transition_order("completed", "refund_pending") == "refund_pending"
    assert transition_order("refund_pending", "refunded") == "refunded"


def test_order_rejects_illegal_jump() -> None:
    with pytest.raises(BadRequestError) as exc:
        transition_order("pending", "completed")
    assert exc.value.details is not None
    assert exc.value.details["current"] == "pending"


def test_terminal_order_states_cannot_move() -> None:
    for state in ("refunded", "cancelled"):
        with pytest.raises(BadRequestError):
            transition_order(state, "paid")


def test_ticket_approval_path() -> None:
    assert transition_ticket("pending", "waiting_approval") == "waiting_approval"
    assert transition_ticket("waiting_approval", "approved") == "approved"
    assert transition_ticket("approved", "resolved") == "resolved"


def test_ticket_rejection_can_return_to_review() -> None:
    assert transition_ticket("waiting_approval", "rejected") == "rejected"
    assert transition_ticket("rejected", "agent_review") == "agent_review"


def test_ticket_cannot_skip_human_approval() -> None:
    with pytest.raises(BadRequestError):
        transition_ticket("pending", "approved")
