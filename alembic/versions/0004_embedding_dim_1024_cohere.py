"""resize embedding column to 1024 dimensions for Cohere embed-english-v3.0 (production)

Revision ID: 0004
Revises: 0003
Create Date: 2026-08-12
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

OLD_DIM = 768
NEW_DIM = 1024


def upgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_document_chunks_embedding")
    # Existing vectors were produced by a different embedding model dimension;
    # they cannot be reinterpreted at the new size, so clear them and let
    # affected documents be reprocessed.
    op.execute("DELETE FROM document_chunks")
    op.alter_column(
        "document_chunks",
        "embedding",
        type_=Vector(NEW_DIM),
        existing_type=Vector(OLD_DIM),
        postgresql_using="NULL",
    )
    op.execute(
        "CREATE INDEX ix_document_chunks_embedding ON document_chunks "
        "USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_document_chunks_embedding")
    op.execute("DELETE FROM document_chunks")
    op.alter_column(
        "document_chunks",
        "embedding",
        type_=Vector(OLD_DIM),
        existing_type=Vector(NEW_DIM),
        postgresql_using="NULL",
    )
    op.execute(
        "CREATE INDEX ix_document_chunks_embedding ON document_chunks "
        "USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)"
    )