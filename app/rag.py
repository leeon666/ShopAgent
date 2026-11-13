"""轻量 RAG：文档切分、确定性向量与检索。"""
from __future__ import annotations

import hashlib
import math
import re
from collections import Counter

from sqlalchemy import select
from sqlalchemy.orm import Session

from .db import KnowledgeChunk, KnowledgeDocument

EMBED_DIM = 128
CHUNK_SIZE = 240
CHUNK_OVERLAP = 40

_TOKEN_RE = re.compile(r"[a-zA-Z0-9]+|[\u4e00-\u9fff]")


def _tokens(text: str) -> list[str]:
    return [t.lower() for t in _TOKEN_RE.findall(text or "")]


def embed(text: str, dim: int = EMBED_DIM) -> list[float]:
    tokens = _tokens(text)
    vector = [0.0] * dim
    if not tokens:
        return vector
    counts = Counter(tokens)
    for token, count in counts.items():
        digest = hashlib.md5(token.encode("utf-8")).hexdigest()
        index = int(digest, 16) % dim
        vector[index] += math.log1p(count)
    norm = math.sqrt(sum(v * v for v in vector)) or 1.0
    return [v / norm for v in vector]


def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if not na or not nb:
        return 0.0
    return dot / (na * nb)


def _split_text(text: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    text = (text or "").strip()
    if not text:
        return []
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    chunks: list[str] = []
    for paragraph in paragraphs:
        start = 0
        while start < len(paragraph):
            end = min(start + size, len(paragraph))
            chunk = paragraph[start:end]
            chunks.append(chunk)
            if end >= len(paragraph):
                break
            start = end - overlap
    return chunks


def ingest_document(
    session: Session,
    title: str,
    content: str,
    source: str = "",
) -> KnowledgeDocument:
    document = KnowledgeDocument(title=title, content=content, source=source, status="active")
    session.add(document)
    session.flush()
    for position, chunk in enumerate(_split_text(content)):
        session.add(
            KnowledgeChunk(
                document_id=document.id,
                position=position,
                content=chunk,
                meta={"source": source, "title": title},
                embedding=embed(chunk),
            )
        )
    session.commit()
    session.refresh(document)
    return document


def search(
    session: Session,
    query: str,
    top_k: int = 5,
) -> list[dict]:
    rows = session.execute(
        select(KnowledgeChunk, KnowledgeDocument)
        .join(KnowledgeDocument, KnowledgeDocument.id == KnowledgeChunk.document_id)
        .where(KnowledgeDocument.status == "active")
    ).all()
    query_vec = embed(query)
    query_tokens = set(_tokens(query))
    scored: list[tuple[float, KnowledgeChunk, KnowledgeDocument]] = []
    for chunk, document in rows:
        vector_score = _cosine(query_vec, chunk.embedding or [])
        chunk_tokens = _tokens(chunk.content)
        overlap = len(query_tokens.intersection(chunk_tokens))
        lexical = overlap / (1 + math.log1p(len(chunk_tokens))) if chunk_tokens else 0.0
        score = max(vector_score, lexical)
        scored.append((score, chunk, document))
    scored.sort(key=lambda item: item[0], reverse=True)
    results = []
    for score, chunk, document in scored[:top_k]:
        results.append(
            {
                "chunk_id": chunk.id,
                "document_id": document.id,
                "title": document.title,
                "source": document.source,
                "position": chunk.position,
                "score": round(score, 4),
                "content": chunk.content,
            }
        )
    return results
