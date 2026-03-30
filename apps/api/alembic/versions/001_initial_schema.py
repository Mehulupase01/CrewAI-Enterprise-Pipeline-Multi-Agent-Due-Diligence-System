"""Initial schema — captures all 14 ORM tables from Phases 1-2.

Revision ID: 001
Revises:
Create Date: 2026-03-30
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "cases",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("target_name", sa.String(255), nullable=False),
        sa.Column("country", sa.String(100), nullable=False, server_default="India"),
        sa.Column("summary", sa.Text, nullable=True),
        sa.Column("motion_pack", sa.String(80), nullable=False),
        sa.Column("sector_pack", sa.String(80), nullable=False),
        sa.Column("status", sa.String(40), nullable=False, server_default="draft"),
    )

    op.create_table(
        "document_artifacts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "case_id",
            sa.String(36),
            sa.ForeignKey("cases.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("original_filename", sa.String(255), nullable=True),
        sa.Column("source_kind", sa.String(80), nullable=False),
        sa.Column("document_kind", sa.String(120), nullable=False),
        sa.Column("mime_type", sa.String(120), nullable=True),
        sa.Column("processing_status", sa.String(40), nullable=False, server_default="received"),
        sa.Column("storage_path", sa.String(500), nullable=True),
        sa.Column("parser_name", sa.String(80), nullable=True),
        sa.Column("sha256_digest", sa.String(64), nullable=True),
        sa.Column("byte_size", sa.Integer, nullable=True),
    )

    op.create_table(
        "evidence_nodes",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "case_id",
            sa.String(36),
            sa.ForeignKey("cases.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "artifact_id",
            sa.String(36),
            sa.ForeignKey("document_artifacts.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("evidence_kind", sa.String(60), nullable=False),
        sa.Column("workstream_domain", sa.String(80), nullable=False),
        sa.Column("citation", sa.String(500), nullable=False),
        sa.Column("excerpt", sa.Text, nullable=False),
        sa.Column("confidence", sa.Float, nullable=False, server_default="0.7"),
    )

    op.create_table(
        "request_items",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "case_id",
            sa.String(36),
            sa.ForeignKey("cases.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("detail", sa.Text, nullable=False),
        sa.Column("status", sa.String(40), nullable=False, server_default="open"),
        sa.Column("owner", sa.String(255), nullable=True),
    )

    op.create_table(
        "qa_items",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "case_id",
            sa.String(36),
            sa.ForeignKey("cases.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("question", sa.Text, nullable=False),
        sa.Column("requested_by", sa.String(255), nullable=True),
        sa.Column("response", sa.Text, nullable=True),
        sa.Column("status", sa.String(40), nullable=False, server_default="open"),
    )

    op.create_table(
        "issue_register_items",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "case_id",
            sa.String(36),
            sa.ForeignKey("cases.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "source_evidence_id",
            sa.String(36),
            sa.ForeignKey("evidence_nodes.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("summary", sa.Text, nullable=False),
        sa.Column("severity", sa.String(40), nullable=False),
        sa.Column("status", sa.String(40), nullable=False, server_default="open"),
        sa.Column("workstream_domain", sa.String(80), nullable=False),
        sa.Column("business_impact", sa.Text, nullable=False),
        sa.Column("recommended_action", sa.Text, nullable=True),
        sa.Column("confidence", sa.Float, nullable=False, server_default="0.75"),
        sa.Column("fingerprint", sa.String(64), nullable=False, unique=True),
    )

    op.create_table(
        "checklist_items",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "case_id",
            sa.String(36),
            sa.ForeignKey("cases.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("template_key", sa.String(255), nullable=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("detail", sa.Text, nullable=False),
        sa.Column("workstream_domain", sa.String(80), nullable=False),
        sa.Column("mandatory", sa.Boolean, nullable=False, server_default="1"),
        sa.Column("evidence_required", sa.Boolean, nullable=False, server_default="1"),
        sa.Column("owner", sa.String(255), nullable=True),
        sa.Column("note", sa.Text, nullable=True),
        sa.Column("status", sa.String(40), nullable=False, server_default="pending"),
        sa.UniqueConstraint("case_id", "template_key"),
    )

    op.create_table(
        "approval_decisions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "case_id",
            sa.String(36),
            sa.ForeignKey("cases.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("reviewer", sa.String(255), nullable=False),
        sa.Column("note", sa.Text, nullable=True),
        sa.Column("decision", sa.String(40), nullable=False),
        sa.Column("rationale", sa.Text, nullable=False),
        sa.Column("ready_for_export", sa.Boolean, nullable=False, server_default="0"),
        sa.Column("open_mandatory_items", sa.Integer, nullable=False, server_default="0"),
        sa.Column("blocking_issue_count", sa.Integer, nullable=False, server_default="0"),
    )

    op.create_table(
        "workflow_runs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "case_id",
            sa.String(36),
            sa.ForeignKey("cases.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("requested_by", sa.String(255), nullable=False),
        sa.Column("note", sa.Text, nullable=True),
        sa.Column("status", sa.String(40), nullable=False, server_default="queued"),
        sa.Column("summary", sa.Text, nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "run_trace_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "run_id",
            sa.String(36),
            sa.ForeignKey("workflow_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("sequence_number", sa.Integer, nullable=False, server_default="1"),
        sa.Column("step_key", sa.String(120), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("message", sa.Text, nullable=False),
        sa.Column("level", sa.String(40), nullable=False, server_default="info"),
    )

    op.create_table(
        "report_bundles",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "case_id",
            sa.String(36),
            sa.ForeignKey("cases.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "run_id",
            sa.String(36),
            sa.ForeignKey("workflow_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("bundle_kind", sa.String(80), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("format", sa.String(40), nullable=False, server_default="markdown"),
        sa.Column("summary", sa.Text, nullable=True),
        sa.Column("content", sa.Text, nullable=False),
    )

    op.create_table(
        "run_export_packages",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "case_id",
            sa.String(36),
            sa.ForeignKey("cases.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "run_id",
            sa.String(36),
            sa.ForeignKey("workflow_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("export_kind", sa.String(80), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("format", sa.String(40), nullable=False, server_default="zip"),
        sa.Column("file_name", sa.String(255), nullable=False),
        sa.Column("summary", sa.Text, nullable=True),
        sa.Column("requested_by", sa.String(255), nullable=False),
        sa.Column("storage_path", sa.String(500), nullable=False),
        sa.Column("sha256_digest", sa.String(64), nullable=False),
        sa.Column("byte_size", sa.Integer, nullable=False, server_default="0"),
        sa.Column("included_files", sa.JSON, nullable=False, server_default="[]"),
    )

    op.create_table(
        "workstream_syntheses",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "case_id",
            sa.String(36),
            sa.ForeignKey("cases.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "run_id",
            sa.String(36),
            sa.ForeignKey("workflow_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("workstream_domain", sa.String(80), nullable=False),
        sa.Column("status", sa.String(40), nullable=False),
        sa.Column("headline", sa.String(255), nullable=False),
        sa.Column("narrative", sa.Text, nullable=False),
        sa.Column("finding_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("blocker_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("confidence", sa.Float, nullable=False, server_default="0.6"),
        sa.Column("recommended_next_action", sa.Text, nullable=False),
    )


def downgrade() -> None:
    op.drop_table("workstream_syntheses")
    op.drop_table("run_export_packages")
    op.drop_table("report_bundles")
    op.drop_table("run_trace_events")
    op.drop_table("workflow_runs")
    op.drop_table("approval_decisions")
    op.drop_table("checklist_items")
    op.drop_table("issue_register_items")
    op.drop_table("qa_items")
    op.drop_table("request_items")
    op.drop_table("evidence_nodes")
    op.drop_table("document_artifacts")
    op.drop_table("cases")
