"""Three-way after-sales evaluation: LLM, LLM+RAG, and full tool agent."""

from __future__ import annotations

import asyncio
import json
import math
import re
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from statistics import mean
from typing import Any
from uuid import uuid4

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_openai import ChatOpenAI

from app.agents.langgraph_assistant import MAX_AGENT_STEPS, PROMPT_VERSION, LangGraphAssistant
from app.agents.tools.rag_tool import search_knowledge_base
from app.agents.tools.shop_tools import READ_ONLY_SHOP_TOOLS
from app.core.config import settings
from app.db.session import get_db_context
from app.repositories import shop as shop_repo
from app.services.user import UserService


def _find_project_data_dir() -> Path:
    for parent in Path(__file__).resolve().parents:
        candidate = parent / "data"
        if (candidate / "evaluation" / "after_sales_cases.json").exists():
            return candidate
    return Path.cwd() / "data"


DATA_DIR = _find_project_data_dir()
DATASET_PATH = DATA_DIR / "evaluation" / "after_sales_cases.json"
RESULTS_DIR = DATA_DIR / "evaluation" / "results"

BASELINE_SYSTEM_PROMPT = """You are evaluating e-commerce after-sales cases.
Choose one intent from the supplied taxonomy and one action from:
approve_refund, approve_return, exchange, reject, manual_review, no_action.
Return only one fenced JSON object with keys: intent, recommended_action,
evidence_sources, missing_information, confidence, requires_human_approval.
Never claim a refund executed. High-risk actions require human approval."""


@dataclass(slots=True)
class CaseResult:
    case_id: str
    mode: str
    latency_ms: int
    input_tokens: int
    output_tokens: int
    output: str
    decision: dict[str, Any] | None
    expected_intent: str
    expected_action: str
    expect_approval: bool
    must_search_policy: bool
    tool_names: list[str]
    tool_successes: int
    tool_failures: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "mode": self.mode,
            "latency_ms": self.latency_ms,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "output": self.output,
            "decision": self.decision,
            "expected_intent": self.expected_intent,
            "expected_action": self.expected_action,
            "expect_approval": self.expect_approval,
            "must_search_policy": self.must_search_policy,
            "tool_names": self.tool_names,
            "tool_successes": self.tool_successes,
            "tool_failures": self.tool_failures,
        }


def load_cases(path: Path = DATASET_PATH) -> list[dict[str, Any]]:
    return json.loads(path.read_text(encoding="utf-8"))


async def resolve_placeholders() -> dict[str, str]:
    async with get_db_context() as db:
        user = await UserService(db).get_by_email("demo@shopagent.example.com")
        orders, _ = await shop_repo.list_orders(db, user.id, 0, 100)
        tickets, _ = await shop_repo.list_tickets(db, user.id, 0, 100)

    paid = next((order for order in orders if order.status == "paid"), None)
    completed = next((order for order in orders if order.status == "completed"), None)
    pending = next((order for order in orders if order.status == "pending"), None)
    damage = next((ticket for ticket in tickets if ticket.type == "damage"), None)
    missing = [
        name
        for name, value in {
            "paid order": paid,
            "completed order": completed,
            "pending order": pending,
            "damage ticket": damage,
        }.items()
        if value is None
    ]
    if missing:
        raise RuntimeError(
            "Demo dataset is incomplete. Run `shopagent_v2 cmd seed-shop` first. "
            f"Missing: {', '.join(missing)}"
        )
    return {
        "{{PAID_ORDER_NO}}": paid.order_no,
        "{{DAMAGED_ORDER_NO}}": completed.order_no,
        "{{PENDING_ORDER_NO}}": pending.order_no,
        "{{DAMAGED_TICKET_NO}}": damage.ticket_no,
    }


def render_prompt(template: str, replacements: dict[str, str]) -> str:
    rendered = template
    for placeholder, value in replacements.items():
        rendered = rendered.replace(placeholder, value)
    return rendered


def parse_decision(output: str) -> dict[str, Any] | None:
    blocks = re.findall(r"```(?:json)?\s*(.*?)```", output, flags=re.DOTALL | re.IGNORECASE)
    candidates = [*reversed(blocks), output]
    for candidate in candidates:
        try:
            parsed = json.loads(candidate.strip())
        except (json.JSONDecodeError, TypeError):
            continue
        if isinstance(parsed, dict) and "recommended_action" in parsed:
            return parsed
    return None


def _message_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict) and block.get("type") == "text":
                parts.append(str(block.get("text") or ""))
        return "".join(parts)
    return str(content or "")


def _usage(messages: list[Any]) -> tuple[int, int]:
    input_tokens = 0
    output_tokens = 0
    for message in messages:
        usage = getattr(message, "usage_metadata", None) or {}
        input_tokens += int(usage.get("input_tokens") or 0)
        output_tokens += int(usage.get("output_tokens") or 0)
    return input_tokens, output_tokens


async def _baseline(
    *,
    mode: str,
    prompt: str,
    taxonomy: list[str],
) -> tuple[str, list[str], int, int, int, int]:
    policy_context = ""
    if mode == "llm_rag":
        policy_context = await search_knowledge_base(
            query=prompt,
            collection="after_sales_policies",
            top_k=5,
        )

    system = (
        f"{BASELINE_SYSTEM_PROMPT}\nIntent taxonomy: {json.dumps(taxonomy, ensure_ascii=False)}"
    )
    user_content = prompt
    if policy_context:
        user_content += f"\n\nRetrieved policy evidence:\n{policy_context}"

    model = ChatOpenAI(
        model=settings.AI_MODEL,
        temperature=0,
        api_key=settings.OPENAI_API_KEY,
        base_url=settings.OPENAI_BASE_URL,
        timeout=90,
        max_retries=2,
    )
    started = time.monotonic()
    response = await model.ainvoke(
        [SystemMessage(content=system), HumanMessage(content=user_content)]
    )
    latency_ms = int((time.monotonic() - started) * 1000)
    output = _message_text(response.content)
    input_tokens, output_tokens = _usage([response])
    tool_names = ["search_after_sales_policy"] if policy_context else []
    failures = 1 if policy_context.startswith('{"ok": false') else 0
    return output, tool_names, latency_ms, input_tokens, output_tokens, failures


async def _full_agent(prompt: str) -> tuple[str, list[str], int, int, int, int, int]:
    async with get_db_context() as db:
        user = await UserService(db).get_by_email("demo@shopagent.example.com")
        user_id = str(user.id)

    assistant = LangGraphAssistant(tools=READ_ONLY_SHOP_TOOLS)
    started = time.monotonic()
    result = await assistant.graph.ainvoke(
        {"messages": [HumanMessage(content=prompt)]},
        config={
            "configurable": {
                "thread_id": f"eval-{uuid4()}",
                "user_id": user_id,
                "trace_id": f"eval-{uuid4()}",
            },
            "recursion_limit": MAX_AGENT_STEPS,
        },
    )
    latency_ms = int((time.monotonic() - started) * 1000)
    messages = result.get("messages", [])
    tool_names: list[str] = []
    successes = 0
    failures = 0
    for message in messages:
        if isinstance(message, AIMessage):
            for tool_call in message.tool_calls or []:
                tool_names.append(str(tool_call.get("name") or ""))
        elif isinstance(message, ToolMessage):
            raw = str(message.content)
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError:
                payload = {}
            if payload.get("ok") is False:
                failures += 1
            else:
                successes += 1

    ai_messages = [message for message in messages if isinstance(message, AIMessage)]
    output = _message_text(ai_messages[-1].content) if ai_messages else ""
    input_tokens, output_tokens = _usage(ai_messages)
    return output, tool_names, latency_ms, input_tokens, output_tokens, successes, failures


async def run_case(
    case: dict[str, Any],
    *,
    mode: str,
    replacements: dict[str, str],
    taxonomy: list[str],
) -> CaseResult:
    prompt = render_prompt(case["prompt"], replacements)
    if mode in {"llm_only", "llm_rag"}:
        output, tools, latency, input_tokens, output_tokens, failures = await _baseline(
            mode=mode, prompt=prompt, taxonomy=taxonomy
        )
        successes = max(0, len(tools) - failures) if mode == "llm_rag" else 0
    elif mode == "full_agent":
        output, tools, latency, input_tokens, output_tokens, successes, failures = await _full_agent(
            prompt
        )
    else:
        raise ValueError(f"Unknown evaluation mode: {mode}")

    return CaseResult(
        case_id=case["id"],
        mode=mode,
        latency_ms=latency,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        output=output,
        decision=parse_decision(output),
        expected_intent=case["expected_intent"],
        expected_action=case["expected_action"],
        expect_approval=bool(case["expect_approval"]),
        must_search_policy=bool(case["must_search_policy"]),
        tool_names=tools,
        tool_successes=successes,
        tool_failures=failures,
    )


def percentile(values: list[int], fraction: float) -> int:
    if not values:
        return 0
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, math.ceil(len(ordered) * fraction) - 1))
    return ordered[index]


def summarize(results: list[CaseResult], cases: list[dict[str, Any]]) -> dict[str, Any]:
    by_mode: dict[str, list[CaseResult]] = {}
    for result in results:
        by_mode.setdefault(result.mode, []).append(result)

    case_by_id = {case["id"]: case for case in cases}
    summary: dict[str, Any] = {}
    for mode, mode_results in by_mode.items():
        decision_count = sum(result.decision is not None for result in mode_results)
        intent_correct = sum(
            (result.decision or {}).get("intent") == result.expected_intent
            for result in mode_results
        )
        action_correct = sum(
            (result.decision or {}).get("recommended_action") == result.expected_action
            for result in mode_results
        )
        policy_cases = [result for result in mode_results if result.must_search_policy]
        citation_covered = sum(
            bool(re.search(r"\[\d+\]", result.output)) for result in policy_cases
        )
        unsupported = 0
        for result in policy_cases:
            action = (result.decision or {}).get("recommended_action")
            if action not in {"manual_review", "reject", "no_action"} and not re.search(
                r"\[\d+\]", result.output
            ):
                unsupported += 1
        approval_cases = [result for result in mode_results if result.expect_approval]
        escalated = sum(
            (result.decision or {}).get("requires_human_approval") is True
            for result in approval_cases
        )

        selected_expected = 0
        expected_tool_total = 0
        for result in mode_results:
            expected = case_by_id[result.case_id]["must_use_tools"]
            if mode == "full_agent":
                expected_tool_total += len(expected)
                selected_expected += sum(tool in result.tool_names for tool in expected)

        tool_attempts = sum(result.tool_successes + result.tool_failures for result in mode_results)
        summary[mode] = {
            "cases": len(mode_results),
            "structured_output_rate": round(decision_count / len(mode_results), 4),
            "intent_accuracy": round(intent_correct / len(mode_results), 4),
            "action_accuracy": round(action_correct / len(mode_results), 4),
            "policy_citation_coverage": round(citation_covered / len(policy_cases), 4)
            if policy_cases
            else None,
            "unsupported_conclusion_rate": round(unsupported / len(policy_cases), 4)
            if policy_cases
            else None,
            "correct_escalation_rate": round(escalated / len(approval_cases), 4)
            if approval_cases
            else None,
            "expected_tool_selection_rate": round(selected_expected / expected_tool_total, 4)
            if mode == "full_agent" and expected_tool_total
            else None,
            "tool_success_rate": round(
                sum(result.tool_successes for result in mode_results) / tool_attempts, 4
            )
            if tool_attempts
            else None,
            "p50_latency_ms": percentile([result.latency_ms for result in mode_results], 0.50),
            "p95_latency_ms": percentile([result.latency_ms for result in mode_results], 0.95),
            "average_input_tokens": round(
                mean(result.input_tokens for result in mode_results), 2
            ),
            "average_output_tokens": round(
                mean(result.output_tokens for result in mode_results), 2
            ),
        }
    return summary


async def evaluate(
    *,
    modes: list[str],
    limit: int | None = None,
    concurrency: int = 3,
    progress: Callable[[int, int, str, str], None] | None = None,
) -> dict[str, Any]:
    cases = load_cases()
    if limit is not None:
        cases = cases[:limit]
    replacements = await resolve_placeholders()
    taxonomy = sorted({case["expected_intent"] for case in cases})
    results: list[CaseResult] = []
    semaphore = asyncio.Semaphore(max(1, concurrency))
    total = len(modes) * len(cases)
    completed = 0

    async def execute(mode: str, case: dict[str, Any]) -> CaseResult:
        nonlocal completed
        async with semaphore:
            try:
                result = await asyncio.wait_for(
                    run_case(
                        case,
                        mode=mode,
                        replacements=replacements,
                        taxonomy=taxonomy,
                    ),
                    timeout=180,
                )
            except Exception as exc:
                result = CaseResult(
                    case_id=case["id"],
                    mode=mode,
                    latency_ms=180_000,
                    input_tokens=0,
                    output_tokens=0,
                    output=f"Evaluation case failed: {exc}",
                    decision=None,
                    expected_intent=case["expected_intent"],
                    expected_action=case["expected_action"],
                    expect_approval=bool(case["expect_approval"]),
                    must_search_policy=bool(case["must_search_policy"]),
                    tool_names=[],
                    tool_successes=0,
                    tool_failures=1,
                )
            completed += 1
            if progress:
                progress(completed, total, mode, case["id"])
            return result

    tasks = [execute(mode, case) for mode in modes for case in cases]
    results = list(await asyncio.gather(*tasks))

    report = {
        "generated_at": datetime.now(UTC).isoformat(),
        "model": settings.AI_MODEL,
        "prompt_version": PROMPT_VERSION,
        "dataset_size": len(cases),
        "modes": modes,
        "summary": summarize(results, cases),
        "results": [result.to_dict() for result in results],
    }
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    output_path = RESULTS_DIR / f"after_sales_{timestamp}.json"
    output_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    report["output_path"] = str(output_path)
    return report


def run_evaluation(
    *,
    modes: list[str],
    limit: int | None = None,
    concurrency: int = 3,
    progress: Callable[[int, int, str, str], None] | None = None,
) -> dict[str, Any]:
    return asyncio.run(
        evaluate(
            modes=modes,
            limit=limit,
            concurrency=concurrency,
            progress=progress,
        )
    )
