"""Tests for the reproducible after-sales evaluation harness."""

import json

from app.evaluation.after_sales import load_cases, parse_decision


def test_dataset_has_thirty_unique_non_trivial_cases() -> None:
    cases = load_cases()
    assert len(cases) >= 30
    assert len({case["id"] for case in cases}) == len(cases)
    assert all(case["prompt"].strip() for case in cases)
    assert {"approve_refund", "approve_return", "manual_review", "reject"} <= {
        case["expected_action"] for case in cases
    }


def test_parse_decision_from_fenced_json() -> None:
    output = """说明文字
```json
{"intent":"quality_refund","recommended_action":"manual_review","evidence_sources":["refund_policy.md"],"missing_information":[],"confidence":0.8,"requires_human_approval":true}
```
"""
    decision = parse_decision(output)
    assert decision is not None
    assert decision["recommended_action"] == "manual_review"


def test_parse_decision_rejects_non_decision_json() -> None:
    output = json.dumps({"message": "not a decision"})
    assert parse_decision(output) is None
