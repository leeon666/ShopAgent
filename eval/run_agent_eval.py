"""售后 Agent 三方案评测：纯规则/纯 LLM 基线、RAG、完整 Agent。"""
from __future__ import annotations

import json
import math
import os
import statistics
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("SHOP_DB_PATH", os.path.join(tempfile.mkdtemp(), "agent_eval.db"))

from app import rag  # noqa: E402
from app.agent.graph import HIGH_RISK_INTENTS, POLICY_INTENTS, _detect_intent, build_graph  # noqa: E402
from app.db import Category, Order, OrderItem, Product, SessionLocal, User, init_db  # noqa: E402
from app.security import hash_password  # noqa: E402


def _load_json(name: str) -> dict:
    return json.loads((Path(__file__).parent / "cases" / name).read_text(encoding="utf-8"))


def _percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, math.ceil(len(ordered) * p) - 1))
    return ordered[index]


def _seed() -> tuple[int, int]:
    with SessionLocal() as session:
        user = User(username="eval-user", password_hash=hash_password("pass1234"), role="user")
        category = Category(name="评测分类", sort=99)
        session.add_all([user, category])
        session.flush()
        product = Product(
            category_id=category.id,
            name="评测商品",
            description="",
            price=59.0,
            stock=100,
            status="on",
        )
        session.add(product)
        session.flush()
        order = Order(
            order_no="EVAL-ORDER-1",
            user_id=user.id,
            total_amount=59.0,
            status="paid",
            paid_at=datetime.now(),
        )
        session.add(order)
        session.flush()
        session.add(
            OrderItem(
                order_id=order.id,
                product_id=product.id,
                product_name=product.name,
                price=product.price,
                quantity=1,
            )
        )
        session.commit()
        return user.id, order.id


def _seed_knowledge() -> None:
    data = _load_json("retrieval_cases.json")
    with SessionLocal() as session:
        for item in data["documents"]:
            rag.ingest_document(session, item["title"], item["content"], item["source"])


def _pure_run(message: str) -> dict:
    intent = _detect_intent(message)
    return {
        "intent": intent,
        "evidence": [],
        "requires_human_approval": intent in HIGH_RISK_INTENTS,
        "recommended_action": "manual_review" if intent in HIGH_RISK_INTENTS else "answer",
    }


def _rag_run(session, message: str) -> dict:
    intent = _detect_intent(message)
    policies = rag.search(session, message, top_k=3)
    policy_required = intent in POLICY_INTENTS
    return {
        "intent": intent,
        "evidence": policies if policy_required else [],
        "requires_human_approval": intent in HIGH_RISK_INTENTS or (policy_required and not policies),
        "recommended_action": "manual_review" if policy_required and not policies else "answer_with_policy",
    }


def _full_run(graph, user_id: int, order_id: int, message: str) -> dict:
    result = graph.invoke(
        {
            "ticket_id": 1,
            "user_id": user_id,
            "request_id": "eval-request",
            "message": message,
            "order_id": order_id,
            "tool_results": {},
            "steps": [],
            "step_count": 0,
            "max_steps": 8,
            "token_budget": 2000,
            "tokens_used": 0,
            "stop_reason": None,
        }
    )
    return {
        "intent": result.get("output", {}).get("intent"),
        "evidence": result.get("output", {}).get("evidence", []),
        "requires_human_approval": result.get("output", {}).get("requires_human_approval", False),
        "recommended_action": result.get("output", {}).get("recommended_action", ""),
        "tokens_used": result.get("tokens_used", 0),
        "tool_results": result.get("tool_results", {}),
        "stop_reason": result.get("stop_reason"),
    }


def main() -> None:
    init_db()
    user_id, order_id = _seed()
    _seed_knowledge()
    cases = _load_json("agent_cases.json")["cases"]
    graph = build_graph()

    modes = {"pure": [], "rag": [], "full": []}
    for case in cases:
        start = time.perf_counter()
        pure = _pure_run(case["message"])
        modes["pure"].append((pure, (time.perf_counter() - start) * 1000, 0))

        start = time.perf_counter()
        with SessionLocal() as session:
            rag_result = _rag_run(session, case["message"])
        modes["rag"].append((rag_result, (time.perf_counter() - start) * 1000, 0))

        start = time.perf_counter()
        full = _full_run(graph, user_id, order_id, case["message"])
        modes["full"].append((full, (time.perf_counter() - start) * 1000, full.get("tokens_used", 0)))

    report = {"case_count": len(cases), "modes": {}}
    for mode, rows in modes.items():
        intent_correct = 0
        approval_correct = 0
        policy_cases = 0
        policy_covered = 0
        tool_total = 0
        tool_ok = 0
        latencies = []
        tokens = []
        for case, (output, latency, token_count) in zip(cases, rows):
            intent_correct += output["intent"] == case["expected_intent"]
            approval_correct += output["requires_human_approval"] == case["expected_requires_approval"]
            if case["expected_intent"] in POLICY_INTENTS:
                policy_cases += 1
                if output["evidence"]:
                    policy_covered += 1
            if mode == "full":
                for tool_result in output.get("tool_results", {}).values():
                    tool_total += 1
                    tool_ok += bool(tool_result.get("ok"))
            latencies.append(latency)
            tokens.append(token_count)
        n = len(cases)
        report["modes"][mode] = {
            "intent_accuracy": round(intent_correct / n, 4),
            "approval_accuracy": round(approval_correct / n, 4),
            "policy_citation_coverage": round(policy_covered / policy_cases, 4) if policy_cases else 1.0,
            "unsupported_policy_rate": round((policy_cases - policy_covered) / policy_cases, 4) if policy_cases else 0.0,
            "tool_success_rate": round(tool_ok / tool_total, 4) if tool_total else None,
            "p50_latency_ms": round(statistics.median(latencies), 2),
            "p95_latency_ms": round(_percentile(latencies, 0.95), 2),
            "avg_tokens": round(sum(tokens) / n, 2),
        }

    report_dir = Path(__file__).parent / "reports"
    report_dir.mkdir(exist_ok=True)
    (report_dir / "agent_latest.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "# Agent 三方案评测报告",
        "",
        f"- 案例数：{len(cases)}",
        "",
        "| 指标 | 纯规则基线 | RAG | 完整 Agent |",
        "|---|---:|---:|---:|",
    ]
    metric_names = [
        ("意图准确率", "intent_accuracy"),
        ("人工审批准确率", "approval_accuracy"),
        ("政策引用覆盖率", "policy_citation_coverage"),
        ("无证据政策结论率", "unsupported_policy_rate"),
        ("工具成功率", "tool_success_rate"),
        ("P50 延迟(ms)", "p50_latency_ms"),
        ("P95 延迟(ms)", "p95_latency_ms"),
        ("平均 Token", "avg_tokens"),
    ]
    for label, key in metric_names:
        values = [report["modes"][mode][key] for mode in ("pure", "rag", "full")]
        lines.append("| {} | {} | {} | {} |".format(label, *["-" if v is None else v for v in values]))
    (report_dir / "agent_latest.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
