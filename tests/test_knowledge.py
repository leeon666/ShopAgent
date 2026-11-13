from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _admin_token() -> str:
    resp = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    assert resp.status_code == 200
    return resp.json()["token"]


def test_knowledge_ingest_and_search():
    headers = {"Authorization": f"Bearer {_admin_token()}"}
    created = client.post(
        "/api/knowledge",
        json={
            "title": "退换货政策",
            "source": "policy/return-v1.md",
            "content": "签收后七日内，商品不影响二次销售且非人为损坏，可以申请七天无理由退货。定制商品和已拆封的贴身衣物不适用。",
        },
        headers=headers,
    )
    assert created.status_code == 200

    result = client.get("/api/knowledge/search", params={"q": "定制商品可以无理由退货吗", "top_k": 3})
    assert result.status_code == 200
    items = result.json()["items"]
    assert items
    assert items[0]["title"] == "退换货政策"
    assert items[0]["source"] == "policy/return-v1.md"
    assert "七天无理由退货" in items[0]["content"]
    assert items[0]["retrieval_mode"] == "hybrid_rrf"
