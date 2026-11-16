"""RAG tool for agent knowledge base search."""

import logging
from typing import TYPE_CHECKING, Any

from app.core.config import settings
from app.core.exceptions import ExternalServiceError
from app.services.rag.embeddings import EmbeddingService
from app.services.rag.retrieval import RetrievalService
from app.services.rag.vectorstore import PgVectorStore

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from app.services.rag.retrieval import BaseRetrievalService

_retrieval_service: "BaseRetrievalService | None" = None


def get_retrieval_service() -> "BaseRetrievalService":
    """Get or create retrieval service singleton."""
    global _retrieval_service
    if _retrieval_service is not None:
        return _retrieval_service

    rag_settings = settings.rag
    embedding_service = EmbeddingService(rag_settings)
    vector_store = PgVectorStore(rag_settings, embedding_service)
    _retrieval_service = RetrievalService(vector_store, rag_settings)
    return _retrieval_service


def _format_results(results: list[Any]) -> str:
    if not results:
        return "知识库中未找到相关内容。"
    formatted = []
    for i, result in enumerate(results, start=1):
        source = result.metadata.get("filename", "未知来源")
        page = result.metadata.get("page_num", "")
        chunk = result.metadata.get("chunk_num", "")
        col = result.metadata.get("collection", "")
        page_info = f", 第 {page} 页" if page else ""
        chunk_info = f", 第 {chunk} 个片段" if chunk else ""
        col_info = f" [{col}]" if col else ""
        formatted.append(
            f"[{i}] 来源: {source}{page_info}{chunk_info}{col_info} (相关度: {result.score:.3f})\n"
            f"{result.content}"
        )
    return (
        "知识库检索结果 (正文中使用 [1]、[2] 等行内引用, 不要在末尾重复列出来源):\n\n"
        + "\n\n".join(formatted)
    )


async def search_knowledge_base(
    query: str,
    collection: str | None = None,
    collections: list[str] | None = None,
    top_k: int = 5,
) -> str:
    """Search the knowledge base and return formatted results.

    Args:
        query: The search query string.
        collection: Name of a single collection. If None, uses settings.rag.collection_name.
        collections: List of collection names for cross-collection search (overrides collection).
        top_k: Number of top results to retrieve (default: 5).
    """
    service: Any = get_retrieval_service()

    default_collection = settings.rag.collection_name
    target_collection = collection or default_collection

    if collections and len(collections) > 1:
        results = await service.retrieve_multi(
            query=query,
            collection_names=collections,
            limit=top_k,
        )
    elif target_collection == "all":
        try:
            all_collections = await service.store.list_collections()
            if not all_collections:
                return "知识库中暂无可用集合。"
            if len(all_collections) == 1:
                results = await service.retrieve(
                    query=query, collection_name=all_collections[0], limit=top_k
                )
            else:
                results = await service.retrieve_multi(
                    query=query, collection_names=all_collections, limit=top_k
                )
        except Exception as e:
            logger.error("Failed to list collections: %s", e, exc_info=True)
            raise ExternalServiceError(
                message="Failed to list knowledge base collections",
                details={"error": str(e)},
            ) from e
    else:
        # If the caller did not name a collection and the configured default
        # has not been populated yet, search the collections that actually
        # exist instead of querying a missing table.
        available = await service.store.list_collections() if collection is None else []
        if collection is None and target_collection not in available:
            if not available:
                return "知识库中暂无可用集合。"
            results = await service.retrieve_multi(
                query=query,
                collection_names=available,
                limit=top_k,
            )
        else:
            results = await service.retrieve(
                query=query,
                collection_name=target_collection,
                limit=top_k,
            )

    return _format_results(results)


__all__ = ["search_knowledge_base"]
