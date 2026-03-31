"""phase 15 enterprise security

Revision ID: 004_phase15_enterprise_security
Revises: 003_phase13_rich_reporting
Create Date: 2026-04-01 11:30:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "004_phase15_enterprise_security"
down_revision = "003_phase13_rich_reporting"
branch_labels = None
depends_on = None


DEFAULT_ORG_ID = "00000000-0000-0000-0000-000000000001"

TENANT_TABLES = [
    "cases",
    "document_artifacts",
    "chunks",
    "evidence_nodes",
    "request_items",
    "qa_items",
    "issue_register_items",
    "checklist_items",
    "approval_decisions",
    "workflow_runs",
    "run_trace_events",
    "report_bundles",
    "run_export_packages",
    "workstream_syntheses",
]


def upgrade() -> None:
    op.create_table(
        "organizations",
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=120), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False, server_default="active"),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )

    op.create_table(
        "audit_logs",
        sa.Column("org_id", sa.String(length=36), nullable=True),
        sa.Column("actor_id", sa.String(length=120), nullable=True),
        sa.Column("actor_email", sa.String(length=255), nullable=True),
        sa.Column("action", sa.String(length=40), nullable=False),
        sa.Column("resource_type", sa.String(length=80), nullable=False),
        sa.Column("resource_id", sa.String(length=36), nullable=True),
        sa.Column("before_state", sa.JSON(), nullable=True),
        sa.Column("after_state", sa.JSON(), nullable=True),
        sa.Column("ip_address", sa.String(length=120), nullable=True),
        sa.Column("request_id", sa.String(length=120), nullable=True),
        sa.Column("status_code", sa.Integer(), nullable=True),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_audit_logs_org_id"), "audit_logs", ["org_id"], unique=False)

    op.create_table(
        "api_clients",
        sa.Column("org_id", sa.String(length=36), nullable=False),
        sa.Column("client_id", sa.String(length=120), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=False),
        sa.Column("client_secret_hash", sa.String(length=128), nullable=False),
        sa.Column("role", sa.String(length=40), nullable=False, server_default="admin"),
        sa.Column("actor_email", sa.String(length=255), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("client_id"),
    )
    op.create_index(op.f("ix_api_clients_org_id"), "api_clients", ["org_id"], unique=False)

    op.execute(
        sa.text(
            """
            INSERT INTO organizations (id, name, slug, status, created_at, updated_at)
            VALUES (:org_id, 'Local Default Organization', 'local-default', 'active', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """
        ).bindparams(org_id=DEFAULT_ORG_ID)
    )

    for table_name in TENANT_TABLES:
        with op.batch_alter_table(table_name) as batch_op:
            batch_op.add_column(
                sa.Column(
                    "org_id",
                    sa.String(length=36),
                    nullable=True,
                )
            )
        op.execute(sa.text(f"UPDATE {table_name} SET org_id = :org_id").bindparams(org_id=DEFAULT_ORG_ID))
        with op.batch_alter_table(table_name) as batch_op:
            batch_op.create_index(batch_op.f(f"ix_{table_name}_org_id"), ["org_id"], unique=False)
            batch_op.create_foreign_key(
                f"fk_{table_name}_org_id_organizations",
                "organizations",
                ["org_id"],
                ["id"],
                ondelete="CASCADE",
            )
            batch_op.alter_column("org_id", nullable=False)


def downgrade() -> None:
    for table_name in reversed(TENANT_TABLES):
        with op.batch_alter_table(table_name) as batch_op:
            batch_op.drop_constraint(f"fk_{table_name}_org_id_organizations", type_="foreignkey")
            batch_op.drop_index(batch_op.f(f"ix_{table_name}_org_id"))
            batch_op.drop_column("org_id")

    op.drop_index(op.f("ix_api_clients_org_id"), table_name="api_clients")
    op.drop_table("api_clients")

    op.drop_index(op.f("ix_audit_logs_org_id"), table_name="audit_logs")
    op.drop_table("audit_logs")

    op.drop_table("organizations")
