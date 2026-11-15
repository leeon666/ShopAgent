"""Persistence helpers for agent runs and tool-level trace steps."""

import logging
from typing import Any
from uuid import UUID

from app.agents.langgraph_assistant import PROMPT_VERSION
from app.db.models.shop import AgentRun
from app.db.session import get_db_context
from app.repositories import shop as shop_repo

logger = logging.getLogger(__name__)


async def start_agent_run(
    *,
    trace_id: str,
    request_id: str | None,
    user_id: UUID,
    conversation_id: str | None,
    model: str,
    prompt: str,
) -> UUID | None:
    try:
        async with get_db_context() as db:
            run = await shop_repo.create_agent_run(
                db,
                trace_id=trace_id,
                request_id=request_id,
                user_id=user_id,
                conversation_id=UUID(conversation_id) if conversation_id else None,
                model=model,
                prompt_version=PROMPT_VERSION,
                prompt=prompt,
            )
            return run.id
    except Exception:
        logger.exception("Failed to create agent run trace")
        return None


async def finish_agent_run(
    *,
    run_id: UUID,
    status: str,
    stop_reason: str,
    usage: dict[str, Any] | None,
    latency_ms: int,
    tool_calls: list[dict[str, Any]],
    error: str = "",
) -> None:
    try:
        usage = usage or {}
        async with get_db_context() as db:
            run = await db.get(AgentRun, run_id)
            if run is None:
                return
            await shop_repo.finish_agent_run(
                db,
                run,
                status=status,
                stop_reason=stop_reason,
                input_tokens=int(usage.get("input_tokens") or 0),
                output_tokens=int(usage.get("output_tokens") or 0),
                total_tokens=int(usage.get("total_tokens") or 0),
                latency_ms=max(0, latency_ms),
                error=error,
            )
            for sequence, tool_call in enumerate(tool_calls, start=1):
                await shop_repo.add_agent_step(
                    db,
                    run_id=run.id,
                    sequence=sequence,
                    node="tool",
                    status=str(tool_call.get("status") or "unknown"),
                    latency_ms=int(tool_call.get("latency_ms") or 0),
                    tool_name=str(tool_call.get("tool_name") or ""),
                    payload={
                        "tool_call_id": tool_call.get("tool_call_id"),
                        "args": tool_call.get("args"),
                        "result": str(tool_call.get("result") or "")[:4_000],
                    },
                    error=str(tool_call.get("error") or ""),
                )
    except Exception:
        logger.exception("Failed to finish agent run trace")
