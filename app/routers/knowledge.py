"""售后政策知识库路由。"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .. import rag
from ..db import KnowledgeDocument, get_db
from ..schemas import KnowledgeIngestRequest
from .deps import get_current_admin

router = APIRouter(prefix="/api/knowledge", tags=["知识库"])


@router.post("", summary="导入知识文档（管理员）")
def ingest_document(
    body: KnowledgeIngestRequest,
    admin: dict = Depends(get_current_admin),
    session: Session = Depends(get_db),
):
    document = rag.ingest_document(session, body.title, body.content, body.source)
    return {"ok": True, "id": document.id, "title": document.title}


@router.get("", summary="知识文档列表（管理员）")
def list_documents(admin: dict = Depends(get_current_admin), session: Session = Depends(get_db)):
    rows = session.scalars(select(KnowledgeDocument).order_by(KnowledgeDocument.id.desc())).all()
    return {
        "items": [
            {
                "id": d.id,
                "title": d.title,
                "source": d.source,
                "status": d.status,
                "created_at": d.created_at,
                "chunk_count": len(d.chunks),
            }
            for d in rows
        ]
    }


@router.get("/search", summary="检索知识库")
def search_knowledge(
    q: str = Query(min_length=1),
    top_k: int = Query(default=5, ge=1, le=20),
    session: Session = Depends(get_db),
):
    results = rag.search(session, q, top_k=top_k)
    return {"query": q, "items": results}
