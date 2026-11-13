import os
import tempfile
import uuid

os.environ["SHOP_DB_PATH"] = os.path.join(tempfile.mkdtemp(), "test.db")

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _register() -> str:
    username = "t" + uuid.uuid4().hex[:10]
    resp = client.post("/api/auth/register", json={"username": username, "password": "pass1234"})
    assert resp.status_code == 200
    return resp.json()["token"]


def _paid_order(token: str) -> dict:
    headers = {"Authorization": f"Bearer {token}"}
    assert client.post("/api/cart", json={"product_id": 1, "quantity": 1}, headers=headers).status_code == 200
    order = client.post("/api/orders", headers=headers).json()
    assert client.post("/api/payment/mock", json={"order_id": order["id"]}, headers=headers).status_code == 200
    return order


def _admin_token() -> str:
    resp = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    assert resp.status_code == 200
    return resp.json()["token"]


def test_aftersales_full_lifecycle():
    token = _register()
    headers = {"Authorization": f"Bearer {token}"}
    order = _paid_order(token)

    created = client.post(
        "/api/after-sales",
        json={"order_id": order["id"], "type": "refund", "reason": "商品破损，申请退货退款"},
        headers=headers,
    )
    assert created.status_code == 200
    ticket = created.json()
    assert ticket["status"] == "pending"

    duplicate = client.post(
        "/api/after-sales",
        json={"order_id": order["id"], "type": "refund", "reason": "重复申请"},
        headers=headers,
    )
    assert duplicate.status_code == 400

    message = client.post(
        f"/api/after-sales/{ticket['id']}/messages",
        json={"content": "请尽快处理"},
        headers=headers,
    )
    assert message.status_code == 200
    assert message.json()["messages"][-1]["content"] == "请尽快处理"

    admin_headers = {"Authorization": f"Bearer {_admin_token()}"}
    reviewing = client.post(
        f"/api/after-sales/{ticket['id']}/review",
        json={"status": "reviewing", "resolution": "进入审核", "refund_amount": 39.0},
        headers=admin_headers,
    )
    assert reviewing.status_code == 200
    assert reviewing.json()["status"] == "reviewing"

    completed = client.post(
        f"/api/after-sales/{ticket['id']}/review",
        json={"status": "completed", "resolution": "审核通过，已退款"},
        headers=admin_headers,
    )
    assert completed.status_code == 200
    assert completed.json()["status"] == "completed"


def test_aftersales_forbidden_for_other_user():
    token = _register()
    headers = {"Authorization": f"Bearer {token}"}
    order = _paid_order(token)
    created = client.post(
        "/api/after-sales",
        json={"order_id": order["id"], "type": "refund", "reason": "测试"},
        headers=headers,
    )
    assert created.status_code == 200
    ticket_id = created.json()["id"]

    other_token = _register()
    other_headers = {"Authorization": f"Bearer {other_token}"}
    denied = client.get(f"/api/after-sales/{ticket_id}", headers=other_headers)
    assert denied.status_code == 403
