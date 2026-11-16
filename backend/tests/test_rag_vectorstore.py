import asyncio
from types import SimpleNamespace

import pytest

from app.agents.tools import rag_tool
from app.api.deps import get_rag_status_service
from app.services.rag.vectorstore import PgVectorStore


def test_vector_collection_tables_use_dedicated_namespace() -> None:
    store = object.__new__(PgVectorStore)

    assert store._table("documents") == "rag_collection_documents"
    assert store._table("after_sales_policies") == "rag_collection_after_sales_policies"
    assert store._legacy_table("after_sales_policies") == "rag_after_sales_policies"


def test_default_collection_falls_back_to_existing_collections(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[list[str]] = []

    class FakeStore:
        async def list_collections(self) -> list[str]:
            return ["after_sales_policies"]

    class FakeRetrievalService:
        store = FakeStore()

        async def retrieve_multi(self, **kwargs: object) -> list[object]:
            calls.append(list(kwargs["collection_names"]))  # type: ignore[arg-type]
            return []

    monkeypatch.setattr(rag_tool, "get_retrieval_service", lambda: FakeRetrievalService())

    result = asyncio.run(rag_tool.search_knowledge_base("灯罩破损怎么处理"))

    assert calls == [["after_sales_policies"]]
    assert result == "知识库中未找到相关内容。"


def test_rag_status_service_receives_shared_redis_client() -> None:
    raw_client = object()
    request = SimpleNamespace(state=SimpleNamespace(redis=SimpleNamespace(raw=raw_client)))

    service = get_rag_status_service(request)  # type: ignore[arg-type]

    assert service._client is raw_client
