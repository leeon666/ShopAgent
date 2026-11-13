"""pgvector knowledge table

Revision ID: 6f2f4e2b4b11
Revises: bf1f9910828f
Create Date: 2026-11-13 20:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector


revision = "6f2f4e2b4b11"
down_revision = "bf1f9910828f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.create_table(
        "knowledge_chunk_vectors",
        sa.Column("chunk_id", sa.Integer(), sa.ForeignKey("knowledge_chunks.id"), primary_key=True),
        sa.Column("embedding", Vector(128), nullable=False),
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_knowledge_chunk_vectors_embedding_hnsw "
        "ON knowledge_chunk_vectors USING hnsw (embedding vector_cosine_ops)"
    )


def downgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    op.drop_table("knowledge_chunk_vectors")
