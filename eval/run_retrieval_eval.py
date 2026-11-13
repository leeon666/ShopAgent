"""售后政策检索评测：计算 Hit@1 / Hit@K / MRR。"""
from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

os.environ.setdefault("SHOP_DB_PATH", os.path.join(tempfile.mkdtemp(), "eval.db"))

from app import rag  # noqa: E402
from app.db import SessionLocal, init_db  # noqa: E402


def _load_cases() -> dict:
    path = Path(__file__).parent / "cases" / "retrieval_cases.json"
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    init_db()
    data = _load_cases()
    doc_id_by_title: dict[str, int] = {}
    with SessionLocal() as session:
        for doc in data["documents"]:
            saved = rag.ingest_document(session, doc["title"], doc["content"], doc["source"])
            doc_id_by_title[saved.title] = saved.id

        rows = []
        hit1 = hitk = 0
        reciprocal_ranks = []
        top_k = 3
        for case in data["cases"]:
            results = rag.search(session, case["query"], top_k=top_k)
            ranked_titles = [item["title"] for item in results]
            relevant = set(case["relevant_titles"])
            first_hit = next((i for i, t in enumerate(ranked_titles) if t in relevant), None)
            if first_hit == 0:
                hit1 += 1
            if first_hit is not None and first_hit < top_k:
                hitk += 1
            rr = 1 / (first_hit + 1) if first_hit is not None else 0.0
            reciprocal_ranks.append(rr)
            rows.append(
                {
                    "query": case["query"],
                    "expected": sorted(relevant),
                    "got": ranked_titles,
                    "first_hit": first_hit,
                    "rr": round(rr, 4),
                }
            )

    total = len(data["cases"])
    report_lines = [
        "# 检索评测报告",
        "",
        f"- 案例数：{total}",
        f"- Hit@1：{hit1}/{total} = {hit1/total:.2%}",
        f"- Hit@{top_k}：{hitk}/{total} = {hitk/total:.2%}",
        f"- MRR：{sum(reciprocal_ranks)/total:.4f}",
        "",
        "| query | expected | got | first_hit | rr |",
        "|---|---|---|---|---|",
    ]
    for row in rows:
        report_lines.append(
            f"| {row['query']} | {', '.join(row['expected'])} | {', '.join(row['got'][:top_k])} | {row['first_hit']} | {row['rr']} |"
        )

    report_dir = Path(__file__).parent / "reports"
    report_dir.mkdir(exist_ok=True)
    report = "\n".join(report_lines) + "\n"
    (report_dir / "retrieval_latest.md").write_text(report, encoding="utf-8")
    print(report)


if __name__ == "__main__":
    main()
