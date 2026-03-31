"""phase 13 rich reporting fields

Revision ID: 003_phase13_rich_reporting
Revises: 002_pgvector_embedding
Create Date: 2026-03-31 17:15:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "003_phase13_rich_reporting"
down_revision = "002_pgvector_embedding"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "workflow_runs",
        sa.Column("report_template", sa.String(length=80), nullable=False, server_default="standard"),
    )
    op.add_column("report_bundles", sa.Column("file_name", sa.String(length=255), nullable=True))
    op.add_column("report_bundles", sa.Column("storage_path", sa.String(length=500), nullable=True))
    op.add_column("report_bundles", sa.Column("sha256_digest", sa.String(length=64), nullable=True))
    op.add_column("report_bundles", sa.Column("byte_size", sa.Integer(), nullable=True))
    op.alter_column("workflow_runs", "report_template", server_default=None)


def downgrade() -> None:
    op.drop_column("report_bundles", "byte_size")
    op.drop_column("report_bundles", "sha256_digest")
    op.drop_column("report_bundles", "storage_path")
    op.drop_column("report_bundles", "file_name")
    op.drop_column("workflow_runs", "report_template")
