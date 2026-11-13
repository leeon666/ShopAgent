import uuid

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _register() -> str:
    username = "a" + uuid.uuid4().hex[:10]
    resp = client.post("/api/auth/register", json={"username": username, "password": "pass1234"})
    assert resp.status_code == 200
    return resp.json()["token"]


def _admin_token() -> str:
    resp = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    assert resp.status_code == 200
    return resp.json()["token"]


def _paid_order(token: str) -> dict:
    headers = {"Authorization": f"Bearer {token}"}
    assert client.post("/api/cart", json={"product_id": 1, "quantity": 1}, headers=headers).status_code == 200
    order = client.post("/api/orders", headers=headers).json()
    assert client.post("/api/payment/mock", json={"order_id": order["id"]}, headers=headers).status_code == 200
    return order


def test_agent_run_with_rag_and_approval():
    admin_headers = {"Authorization": f"Bearer {_admin_token()}"}
    client.post(
        "/api/knowledge",
        json={
            "title": "退款审批测试政策",
            "source": "policy/test-refund.md",
            "content": "商品破损时，签收后七日内可以申请退货退款。退款需要审核，金额超过一百元时必须人工审批。",
        },
        headers=admin_headers,
    )

    token = _register()
    headers = {"Authorization": f"Bearer {token}"}
    order = _paid_order(token)
    ticket = client.post(
        "/api/after-sales",
        json={"order_id": order["id"], "type": "damage", "reason": "商品破损，想退款"},
        headers=headers,
    ).json()

    run = client.post(
        f"/api/agent-runs/tickets/{ticket['id']}",
        json={"message": "商品破损，想申请退款"},
        headers=headers,
    )
    assert run.status_code == 200
    data = run.json()
    assert data["status"] == "completed"
    assert data["stop_reason"] == "human_approval_required"
    assert run.headers["X-Request-ID"] == data["request_id"]
    assert data["model_name"] == "rules-fallback"
    assert data["prompt_version"] == "shopagent-agent-v1"
    assert data["latency_ms"] > 0
    assert data["output"]["intent"] == "damage"
    assert data["output"]["evidence"]
    assert data["output"]["requires_human_approval"] is True
    assert data["steps"]
    assert data["steps"][0]["duration_ms"] >= 0

    fetched = client.get(f"/api/agent-runs/{data['id']}", headers=headers)
    assert fetched.status_code == 200
    assert fetched.json()["output"]["recommended_action"] == "create_refund_review"


def test_agent_sse_stream():
    token = _register()
    headers = {"Authorization": f"Bearer {token}"}
    order = _paid_order(token)
    ticket = client.post(
        "/api/after-sales",
        json={"order_id": order["id"], "type": "logistics", "reason": "物流不更新"},
        headers=headers,
    ).json()

    with client.stream(
        "POST",
        f"/api/agent-runs/tickets/{ticket['id']}/stream",
        json={"message": "物流一直不更新"},
        headers=headers,
    ) as response:
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/event-stream")
        body = "".join(response.iter_text())

    assert '"event": "run_started"' in body
    assert '"event": "node"' in body
    assert '"event": "completed"' in body


def test_agent_compresses_long_conversation():
    token = _register()
    headers = {"Authorization": f"Bearer {token}"}
    order = _paid_order(token)
    ticket = client.post(
        "/api/after-sales",
        json={"order_id": order["id"], "type": "refund", "reason": "需要退款"},
        headers=headers,
    ).json()
    long_text = "这是顾客提供的详细问题说明。" * 20
    for _ in range(8):
        client.post(
            f"/api/after-sales/{ticket['id']}/messages",
            json={"content": long_text},
            headers=headers,
        )

    run = client.post(
        f"/api/agent-runs/tickets/{ticket['id']}",
        json={"message": "可以退款吗"},
        headers=headers,
    )
    assert run.status_code == 200
    data = run.json()
    assert data["output"]["context_compressed"] is True
    assert data["steps"][0]["detail"]["context_compressed"] is True
