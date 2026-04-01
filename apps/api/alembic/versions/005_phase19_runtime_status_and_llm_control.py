"""phase 19 runtime status and llm control

Revision ID: 005_phase19_runtime_status_and_llm_control
Revises: 004_phase15_enterprise_security
Create Date: 2026-04-01 13:30:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "005_phase19_runtime_status_and_llm_control"
down_revision = "004_phase15_enterprise_security"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "org_runtime_configs",
        sa.Column("org_id", sa.String(length=36), nullable=False),
        sa.Column("llm_provider", sa.String(length=80), nullable=True),
        sa.Column("llm_model", sa.String(length=255), nullable=True),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("org_id"),
    )
    op.create_index(
        op.f("ix_org_runtime_configs_org_id"),
        "org_runtime_configs",
        ["org_id"],
        unique=False,
    )

    op.create_table(
        "dependency_statuses",
        sa.Column("dependency_name", sa.String(length=120), nullable=False),
        sa.Column("category", sa.String(length=40), nullable=False),
        sa.Column("mode", sa.String(length=40), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("detail", sa.Text(), nullable=False),
        sa.Column("latency_ms", sa.Float(), nullable=False, server_default="0"),
        sa.Column("last_checked_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_success_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("dependency_name"),
    )

    with op.batch_alter_table("workflow_runs") as batch_op:
        batch_op.add_column(
            sa.Column("requested_llm_provider_override", sa.String(length=80), nullable=True)
        )
        batch_op.add_column(
            sa.Column("requested_llm_model_override", sa.String(length=255), nullable=True)
        )
        batch_op.add_column(sa.Column("effective_llm_provider", sa.String(length=80), nullable=True))
        batch_op.add_column(sa.Column("effective_llm_model", sa.String(length=255), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("workflow_runs") as batch_op:
        batch_op.drop_column("effective_llm_model")
        batch_op.drop_column("effective_llm_provider")
        batch_op.drop_column("requested_llm_model_override")
        batch_op.drop_column("requested_llm_provider_override")

    op.drop_table("dependency_statuses")

    op.drop_index(op.f("ix_org_runtime_configs_org_id"), table_name="org_runtime_configs")
    op.drop_table("org_runtime_configs")
