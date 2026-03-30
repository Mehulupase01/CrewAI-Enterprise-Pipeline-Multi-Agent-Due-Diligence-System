"""Add pgvector extension and embedding column to chunks table.

Revision ID: 002
Revises: 001
Create Date: 2026-03-30
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "002"
down_revision: str = "001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Enable pgvector extension (requires superuser or CREATE EXTENSION privilege)
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # Add embedding vector column (nullable — populated asynchronously)
    op.add_column(
        "chunks",
        sa.Column("embedding", sa.LargeBinary(), nullable=True),
    )

    # HNSW index for cosine similarity search on embeddings
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_chunk_embedding "
        "ON chunks USING hnsw ((embedding::vector(1536)) vector_cosine_ops)"
    )

    # GIN index for full-text search (BM25)
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_chunk_tsv "
        "ON chunks USING gin (to_tsvector('english', text))"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_chunk_tsv")
    op.execute("DROP INDEX IF EXISTS idx_chunk_embedding")
    op.drop_column("chunks", "embedding")
    op.execute("DROP EXTENSION IF EXISTS vector")
