from app.agent import llm


class FakeResponse:
    def raise_for_status(self):
        return None

    def json(self):
        return {"choices": [{"message": {"content": "模型生成的售后摘要"}}]}


class FakeClient:
    def __init__(self, timeout):
        self.timeout = timeout

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return None

    def post(self, url, json, headers):
        assert url.endswith("/chat/completions")
        assert json["model"] == "test-model"
        assert json["messages"][0]["role"] == "system"
        assert headers["Authorization"] == "Bearer test-key"
        return FakeResponse()


def test_openai_compatible_client(monkeypatch):
    monkeypatch.setattr(llm, "OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(llm, "OPENAI_BASE_URL", "https://example.test/v1")
    monkeypatch.setattr(llm, "OPENAI_MODEL", "test-model")
    monkeypatch.setattr(llm.httpx, "Client", FakeClient)

    result = llm.complete_text("system", "user")
    assert result == "模型生成的售后摘要"
