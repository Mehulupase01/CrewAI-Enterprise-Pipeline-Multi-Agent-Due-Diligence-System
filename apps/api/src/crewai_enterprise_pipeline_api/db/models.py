from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from crewai_enterprise_pipeline_api.db.base import Base, TimestampedMixin


class CaseRecord(TimestampedMixin, Base):
    __tablename__ = "cases"

    name: Mapped[str] = mapped_column(String(255))
    target_name: Mapped[str] = mapped_column(String(255))
    country: Mapped[str] = mapped_column(String(100), default="India")
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    motion_pack: Mapped[str] = mapped_column(String(80))
    sector_pack: Mapped[str] = mapped_column(String(80))
    status: Mapped[str] = mapped_column(String(40), default="draft")

    documents: Mapped[list[DocumentArtifactRecord]] = relationship(
        back_populates="case",
        cascade="all, delete-orphan",
        order_by="DocumentArtifactRecord.created_at",
        lazy="selectin",
    )
    evidence_items: Mapped[list[EvidenceNodeRecord]] = relationship(
        back_populates="case",
        cascade="all, delete-orphan",
        order_by="EvidenceNodeRecord.created_at",
        lazy="selectin",
    )
    request_items: Mapped[list[RequestItemRecord]] = relationship(
        back_populates="case",
        cascade="all, delete-orphan",
        order_by="RequestItemRecord.created_at",
        lazy="selectin",
    )
    qa_items: Mapped[list[QaItemRecord]] = relationship(
        back_populates="case",
        cascade="all, delete-orphan",
        order_by="QaItemRecord.created_at",
        lazy="selectin",
    )
    issues: Mapped[list[IssueRegisterItemRecord]] = relationship(
        back_populates="case",
        cascade="all, delete-orphan",
        order_by="IssueRegisterItemRecord.created_at",
        lazy="selectin",
    )
    checklist_items: Mapped[list[ChecklistItemRecord]] = relationship(
        back_populates="case",
        cascade="all, delete-orphan",
        order_by="ChecklistItemRecord.created_at",
        lazy="selectin",
    )
    approvals: Mapped[list[ApprovalDecisionRecord]] = relationship(
        back_populates="case",
        cascade="all, delete-orphan",
        order_by="ApprovalDecisionRecord.created_at",
        lazy="selectin",
    )
    workflow_runs: Mapped[list[WorkflowRunRecord]] = relationship(
        back_populates="case",
        cascade="all, delete-orphan",
        order_by="WorkflowRunRecord.created_at",
        lazy="selectin",
    )


class DocumentArtifactRecord(TimestampedMixin, Base):
    __tablename__ = "document_artifacts"

    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column(String(255))
    original_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source_kind: Mapped[str] = mapped_column(String(80))
    document_kind: Mapped[str] = mapped_column(String(120))
    mime_type: Mapped[str | None] = mapped_column(String(120), nullable=True)
    processing_status: Mapped[str] = mapped_column(String(40), default="received")
    storage_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    parser_name: Mapped[str | None] = mapped_column(String(80), nullable=True)
    sha256_digest: Mapped[str | None] = mapped_column(String(64), nullable=True)
    byte_size: Mapped[int | None] = mapped_column(nullable=True)

    case: Mapped[CaseRecord] = relationship(back_populates="documents")


class EvidenceNodeRecord(TimestampedMixin, Base):
    __tablename__ = "evidence_nodes"

    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"))
    artifact_id: Mapped[str | None] = mapped_column(
        ForeignKey("document_artifacts.id", ondelete="SET NULL"),
        nullable=True,
    )
    title: Mapped[str] = mapped_column(String(255))
    evidence_kind: Mapped[str] = mapped_column(String(60))
    workstream_domain: Mapped[str] = mapped_column(String(80))
    citation: Mapped[str] = mapped_column(String(500))
    excerpt: Mapped[str] = mapped_column(Text)
    confidence: Mapped[float] = mapped_column(default=0.7)

    case: Mapped[CaseRecord] = relationship(back_populates="evidence_items")


class RequestItemRecord(TimestampedMixin, Base):
    __tablename__ = "request_items"

    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column(String(255))
    detail: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(40), default="open")
    owner: Mapped[str | None] = mapped_column(String(255), nullable=True)

    case: Mapped[CaseRecord] = relationship(back_populates="request_items")


class QaItemRecord(TimestampedMixin, Base):
    __tablename__ = "qa_items"

    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"))
    question: Mapped[str] = mapped_column(Text)
    requested_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    response: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(40), default="open")

    case: Mapped[CaseRecord] = relationship(back_populates="qa_items")


class IssueRegisterItemRecord(TimestampedMixin, Base):
    __tablename__ = "issue_register_items"

    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"))
    source_evidence_id: Mapped[str | None] = mapped_column(
        ForeignKey("evidence_nodes.id", ondelete="SET NULL"),
        nullable=True,
    )
    title: Mapped[str] = mapped_column(String(255))
    summary: Mapped[str] = mapped_column(Text)
    severity: Mapped[str] = mapped_column(String(40))
    status: Mapped[str] = mapped_column(String(40), default="open")
    workstream_domain: Mapped[str] = mapped_column(String(80))
    business_impact: Mapped[str] = mapped_column(Text)
    recommended_action: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[float] = mapped_column(default=0.75)
    fingerprint: Mapped[str] = mapped_column(String(64), unique=True)

    case: Mapped[CaseRecord] = relationship(back_populates="issues")


class ChecklistItemRecord(TimestampedMixin, Base):
    __tablename__ = "checklist_items"
    __table_args__ = (UniqueConstraint("case_id", "template_key"),)

    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"))
    template_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    title: Mapped[str] = mapped_column(String(255))
    detail: Mapped[str] = mapped_column(Text)
    workstream_domain: Mapped[str] = mapped_column(String(80))
    mandatory: Mapped[bool] = mapped_column(Boolean, default=True)
    evidence_required: Mapped[bool] = mapped_column(Boolean, default=True)
    owner: Mapped[str | None] = mapped_column(String(255), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(40), default="pending")

    case: Mapped[CaseRecord] = relationship(back_populates="checklist_items")


class ApprovalDecisionRecord(TimestampedMixin, Base):
    __tablename__ = "approval_decisions"

    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"))
    reviewer: Mapped[str] = mapped_column(String(255))
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    decision: Mapped[str] = mapped_column(String(40))
    rationale: Mapped[str] = mapped_column(Text)
    ready_for_export: Mapped[bool] = mapped_column(Boolean, default=False)
    open_mandatory_items: Mapped[int] = mapped_column(default=0)
    blocking_issue_count: Mapped[int] = mapped_column(default=0)

    case: Mapped[CaseRecord] = relationship(back_populates="approvals")


class WorkflowRunRecord(TimestampedMixin, Base):
    __tablename__ = "workflow_runs"

    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"))
    requested_by: Mapped[str] = mapped_column(String(255))
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(40), default="queued")
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(nullable=True)

    case: Mapped[CaseRecord] = relationship(back_populates="workflow_runs")
    trace_events: Mapped[list[RunTraceEventRecord]] = relationship(
        back_populates="run",
        cascade="all, delete-orphan",
        order_by="RunTraceEventRecord.sequence_number",
        lazy="selectin",
    )
    report_bundles: Mapped[list[ReportBundleRecord]] = relationship(
        back_populates="run",
        cascade="all, delete-orphan",
        order_by="ReportBundleRecord.created_at",
        lazy="selectin",
    )
    workstream_syntheses: Mapped[list[WorkstreamSynthesisRecord]] = relationship(
        back_populates="run",
        cascade="all, delete-orphan",
        order_by="WorkstreamSynthesisRecord.workstream_domain",
        lazy="selectin",
    )


class RunTraceEventRecord(TimestampedMixin, Base):
    __tablename__ = "run_trace_events"

    run_id: Mapped[str] = mapped_column(ForeignKey("workflow_runs.id", ondelete="CASCADE"))
    sequence_number: Mapped[int] = mapped_column(default=1)
    step_key: Mapped[str] = mapped_column(String(120))
    title: Mapped[str] = mapped_column(String(255))
    message: Mapped[str] = mapped_column(Text)
    level: Mapped[str] = mapped_column(String(40), default="info")

    run: Mapped[WorkflowRunRecord] = relationship(back_populates="trace_events")


class ReportBundleRecord(TimestampedMixin, Base):
    __tablename__ = "report_bundles"

    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"))
    run_id: Mapped[str] = mapped_column(ForeignKey("workflow_runs.id", ondelete="CASCADE"))
    bundle_kind: Mapped[str] = mapped_column(String(80))
    title: Mapped[str] = mapped_column(String(255))
    format: Mapped[str] = mapped_column(String(40), default="markdown")
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    content: Mapped[str] = mapped_column(Text)

    run: Mapped[WorkflowRunRecord] = relationship(back_populates="report_bundles")


class WorkstreamSynthesisRecord(TimestampedMixin, Base):
    __tablename__ = "workstream_syntheses"

    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"))
    run_id: Mapped[str] = mapped_column(ForeignKey("workflow_runs.id", ondelete="CASCADE"))
    workstream_domain: Mapped[str] = mapped_column(String(80))
    status: Mapped[str] = mapped_column(String(40))
    headline: Mapped[str] = mapped_column(String(255))
    narrative: Mapped[str] = mapped_column(Text)
    finding_count: Mapped[int] = mapped_column(default=0)
    blocker_count: Mapped[int] = mapped_column(default=0)
    confidence: Mapped[float] = mapped_column(default=0.6)
    recommended_next_action: Mapped[str] = mapped_column(Text)

    run: Mapped[WorkflowRunRecord] = relationship(back_populates="workstream_syntheses")
