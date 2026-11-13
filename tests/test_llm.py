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


class JsonResponse:
    def raise_for_status(self):
        return None

    def json(self):
        return {
            "model": "test-model",
            "choices": [{"message": {"content": '{"intent":"refund","tools":["get_order"]}'}}],
            "usage": {"total_tokens": 42},
        }


class JsonClient(FakeClient):
    def post(self, url, json, headers):
        assert json["response_format"] == {"type": "json_object"}
        return JsonResponse()


def test_openai_compatible_client(monkeypatch):
    monkeypatch.setattr(llm, "OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(llm, "OPENAI_BASE_URL", "https://example.test/v1")
    monkeypatch.setattr(llm, "OPENAI_MODEL", "test-model")
    monkeypatch.setattr(llm.httpx, "Client", FakeClient)

    result = llm.complete_text("system", "user")
    assert result == "模型生成的售后摘要"


def test_openai_compatible_json_client(monkeypatch):
    monkeypatch.setattr(llm, "OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(llm, "OPENAI_BASE_URL", "https://example.test/v1")
    monkeypatch.setattr(llm, "OPENAI_MODEL", "test-model")
    monkeypatch.setattr(llm.httpx, "Client", JsonClient)

    result = llm.complete_json("system", "user")
    assert result["data"]["intent"] == "refund"
    assert result["usage"]["total_tokens"] == 42
