"""轻量 RAG：文档切分、确定性向量与检索。"""
from __future__ import annotations

import hashlib
import math
import re
from collections import Counter

from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import DATABASE_URL
from .db import KnowledgeChunk, KnowledgeDocument

if DATABASE_URL.startswith(("postgresql", "postgres")):
    from .db import KnowledgeChunkVector

EMBED_DIM = 128
CHUNK_SIZE = 240
CHUNK_OVERLAP = 40

_TOKEN_RE = re.compile(r"[a-zA-Z0-9]+|[\u4e00-\u9fff]")


def _tokens(text: str) -> list[str]:
    return [t.lower() for t in _TOKEN_RE.findall(text or "")]


def _search_tokens(text: str) -> list[str]:
    raw = _tokens(text)
    tokens = list(raw)
    cjk = [token for token in raw if re.fullmatch(r"[\u4e00-\u9fff]", token)]
    tokens.extend(f"{cjk[index]}{cjk[index + 1]}" for index in range(len(cjk) - 1))
    return tokens


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


def _bm25_ranking(
    rows: list[tuple[KnowledgeChunk, KnowledgeDocument]],
    query: str,
) -> list[tuple[int, float, KnowledgeChunk, KnowledgeDocument]]:
    query_tokens = _search_tokens(query)
    if not query_tokens or not rows:
        return []
    tokenized = [(chunk, document, _search_tokens(chunk.content)) for chunk, document in rows]
    doc_freq: Counter[str] = Counter()
    for _chunk, _document, tokens in tokenized:
        doc_freq.update(set(tokens))
    avg_len = sum(len(tokens) for _chunk, _document, tokens in tokenized) / max(1, len(tokenized))
    total_docs = len(tokenized)
    q_counts = Counter(query_tokens)
    scores = []
    for chunk, document, tokens in tokenized:
        tf = Counter(tokens)
        score = 0.0
        for token, query_count in q_counts.items():
            frequency = tf.get(token, 0)
            if not frequency:
                continue
            idf = math.log(1 + (total_docs - doc_freq[token] + 0.5) / (doc_freq[token] + 0.5))
            denominator = frequency + 1.5 * (1 - 0.75 + 0.75 * len(tokens) / max(1.0, avg_len))
            score += query_count * idf * (frequency * 2.5) / denominator
        if score > 0:
            scores.append((chunk.id, score, chunk, document))
    scores.sort(key=lambda item: item[1], reverse=True)
    return scores


def _rrf_fuse(
    vector_ranking: list[tuple[int, float]],
    lexical_ranking: list[tuple[int, float]],
    row_by_id: dict[int, tuple[KnowledgeChunk, KnowledgeDocument]],
    top_k: int,
    rrf_k: int = 60,
    vector_weight: float = 1.0,
    lexical_weight: float = 0.15,
) -> list[dict]:
    vector_score = dict(vector_ranking)
    lexical_score = dict(lexical_ranking)
    if lexical_ranking:
        top_lexical = lexical_ranking[0][1]
        second_lexical = lexical_ranking[1][1] if len(lexical_ranking) > 1 else 0.0
        if top_lexical >= 1.0 and top_lexical > second_lexical * 2:
            lexical_weight = max(lexical_weight, 1.0)
    fused: dict[int, float] = {}
    for rank, (chunk_id, _score) in enumerate(vector_ranking):
        fused[chunk_id] = fused.get(chunk_id, 0.0) + vector_weight / (rrf_k + rank + 1)
    for rank, (chunk_id, _score) in enumerate(lexical_ranking):
        fused[chunk_id] = fused.get(chunk_id, 0.0) + lexical_weight / (rrf_k + rank + 1)
    ranked = sorted(
        fused.items(),
        key=lambda item: (
            item[1],
            lexical_score.get(item[0], 0.0),
            vector_score.get(item[0], 0.0),
        ),
        reverse=True,
    )[:top_k]
    results = []
    for chunk_id, score in ranked:
        chunk, document = row_by_id[chunk_id]
        results.append(
            {
                "chunk_id": chunk.id,
                "document_id": document.id,
                "title": document.title,
                "source": document.source,
                "position": chunk.position,
                "score": round(score, 6),
                "vector_score": round(vector_score.get(chunk_id, 0.0), 6),
                "lexical_score": round(lexical_score.get(chunk_id, 0.0), 6),
                "retrieval_mode": "hybrid_rrf",
                "content": chunk.content,
            }
        )
    return results


def ingest_document(
    session: Session,
    title: str,
    content: str,
    source: str = "",
) -> KnowledgeDocument:
    document = KnowledgeDocument(title=title, content=content, source=source, status="active")
    session.add(document)
    session.flush()
    chunks: list[KnowledgeChunk] = []
    for position, chunk in enumerate(_split_text(content)):
        row = KnowledgeChunk(
            document_id=document.id,
            position=position,
            content=chunk,
            meta={"source": source, "title": title},
            embedding=embed(chunk),
        )
        session.add(row)
        chunks.append(row)
    session.flush()
    if DATABASE_URL.startswith(("postgresql", "postgres")):
        for row in chunks:
            session.add(KnowledgeChunkVector(chunk_id=row.id, embedding=row.embedding))
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
    row_by_id = {chunk.id: (chunk, document) for chunk, document in rows}
    lexical_rows = _bm25_ranking(rows, query)
    lexical_ranking = [(chunk_id, score) for chunk_id, score, _chunk, _document in lexical_rows]

    query_vec = embed(query)
    if DATABASE_URL.startswith(("postgresql", "postgres")):
        distance = KnowledgeChunkVector.embedding.cosine_distance(query_vec).label("distance")
        vector_rows = session.execute(
            select(KnowledgeChunk.id, distance)
            .join(KnowledgeDocument, KnowledgeDocument.id == KnowledgeChunk.document_id)
            .join(KnowledgeChunkVector, KnowledgeChunkVector.chunk_id == KnowledgeChunk.id)
            .where(KnowledgeDocument.status == "active")
            .order_by(distance)
            .limit(max(top_k * 4, 20))
        ).all()
        vector_ranking = [(chunk_id, 1 - float(dist)) for chunk_id, dist in vector_rows]
    else:
        scores = [
            (chunk.id, _cosine(query_vec, chunk.embedding or []))
            for chunk, _document in rows
        ]
        scores.sort(key=lambda item: item[1], reverse=True)
        vector_ranking = scores[: max(top_k * 4, 20)]

    return _rrf_fuse(vector_ranking, lexical_ranking, row_by_id, top_k)
