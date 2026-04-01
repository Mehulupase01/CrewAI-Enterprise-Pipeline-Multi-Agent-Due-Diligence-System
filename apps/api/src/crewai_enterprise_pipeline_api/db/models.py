from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    ForeignKey,
    LargeBinary,
    String,
    Text,
    UniqueConstraint,
    event,
    inspect,
)
from sqlalchemy.orm import Mapped, Session, mapped_column, relationship, with_loader_criteria

from crewai_enterprise_pipeline_api.db.base import Base, TenantScopedMixin, TimestampedMixin


class OrganizationRecord(TimestampedMixin, Base):
    __tablename__ = "organizations"

    name: Mapped[str] = mapped_column(String(255))
    slug: Mapped[str] = mapped_column(String(120), unique=True)
    status: Mapped[str] = mapped_column(String(40), default="active")


class ApiClientRecord(TenantScopedMixin, TimestampedMixin, Base):
    __tablename__ = "api_clients"

    client_id: Mapped[str] = mapped_column(String(120), unique=True)
    display_name: Mapped[str] = mapped_column(String(255))
    client_secret_hash: Mapped[str] = mapped_column(String(128))
    role: Mapped[str] = mapped_column(String(40), default="admin")
    actor_email: Mapped[str] = mapped_column(String(255))
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class AuditLogRecord(TimestampedMixin, Base):
    __tablename__ = "audit_logs"

    org_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("organizations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    actor_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    actor_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    action: Mapped[str] = mapped_column(String(40))
    resource_type: Mapped[str] = mapped_column(String(80))
    resource_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    before_state: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    after_state: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(120), nullable=True)
    request_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    status_code: Mapped[int | None] = mapped_column(nullable=True)


class OrgRuntimeConfigRecord(TenantScopedMixin, TimestampedMixin, Base):
    __tablename__ = "org_runtime_configs"
    __table_args__ = (UniqueConstraint("org_id"),)

    llm_provider: Mapped[str | None] = mapped_column(String(80), nullable=True)
    llm_model: Mapped[str | None] = mapped_column(String(255), nullable=True)


class DependencyStatusRecord(TimestampedMixin, Base):
    __tablename__ = "dependency_statuses"

    dependency_name: Mapped[str] = mapped_column(String(120), unique=True)
    category: Mapped[str] = mapped_column(String(40))
    mode: Mapped[str] = mapped_column(String(40))
    status: Mapped[str] = mapped_column(String(40))
    detail: Mapped[str] = mapped_column(Text)
    latency_ms: Mapped[float] = mapped_column(default=0.0)
    last_checked_at: Mapped[datetime] = mapped_column()
    last_success_at: Mapped[datetime | None] = mapped_column(nullable=True)
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)


class CaseRecord(TenantScopedMixin, TimestampedMixin, Base):
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


class DocumentArtifactRecord(TenantScopedMixin, TimestampedMixin, Base):
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
    chunks: Mapped[list[ChunkRecord]] = relationship(
        back_populates="artifact",
        cascade="all, delete-orphan",
        order_by="ChunkRecord.chunk_index",
        lazy="selectin",
    )


class ChunkRecord(TenantScopedMixin, TimestampedMixin, Base):
    __tablename__ = "chunks"

    artifact_id: Mapped[str] = mapped_column(
        ForeignKey("document_artifacts.id", ondelete="CASCADE"),
    )
    chunk_index: Mapped[int] = mapped_column(default=0)
    section_title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    text: Mapped[str] = mapped_column(Text)
    page_number: Mapped[int | None] = mapped_column(nullable=True)
    char_start: Mapped[int] = mapped_column(default=0)
    char_end: Mapped[int] = mapped_column(default=0)
    has_embedding: Mapped[bool] = mapped_column(Boolean, default=False)
    embedding: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)

    artifact: Mapped[DocumentArtifactRecord] = relationship(back_populates="chunks")


class EvidenceNodeRecord(TenantScopedMixin, TimestampedMixin, Base):
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


class RequestItemRecord(TenantScopedMixin, TimestampedMixin, Base):
    __tablename__ = "request_items"

    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column(String(255))
    detail: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(40), default="open")
    owner: Mapped[str | None] = mapped_column(String(255), nullable=True)

    case: Mapped[CaseRecord] = relationship(back_populates="request_items")


class QaItemRecord(TenantScopedMixin, TimestampedMixin, Base):
    __tablename__ = "qa_items"

    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"))
    question: Mapped[str] = mapped_column(Text)
    requested_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    response: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(40), default="open")

    case: Mapped[CaseRecord] = relationship(back_populates="qa_items")


class IssueRegisterItemRecord(TenantScopedMixin, TimestampedMixin, Base):
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


class ChecklistItemRecord(TenantScopedMixin, TimestampedMixin, Base):
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


class ApprovalDecisionRecord(TenantScopedMixin, TimestampedMixin, Base):
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


class WorkflowRunRecord(TenantScopedMixin, TimestampedMixin, Base):
    __tablename__ = "workflow_runs"

    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"))
    requested_by: Mapped[str] = mapped_column(String(255))
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    report_template: Mapped[str] = mapped_column(String(80), default="standard")
    requested_llm_provider_override: Mapped[str | None] = mapped_column(String(80), nullable=True)
    requested_llm_model_override: Mapped[str | None] = mapped_column(String(255), nullable=True)
    effective_llm_provider: Mapped[str | None] = mapped_column(String(80), nullable=True)
    effective_llm_model: Mapped[str | None] = mapped_column(String(255), nullable=True)
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
    export_packages: Mapped[list[RunExportPackageRecord]] = relationship(
        back_populates="run",
        cascade="all, delete-orphan",
        order_by="RunExportPackageRecord.created_at",
        lazy="selectin",
    )
    workstream_syntheses: Mapped[list[WorkstreamSynthesisRecord]] = relationship(
        back_populates="run",
        cascade="all, delete-orphan",
        order_by="WorkstreamSynthesisRecord.workstream_domain",
        lazy="selectin",
    )


class RunTraceEventRecord(TenantScopedMixin, TimestampedMixin, Base):
    __tablename__ = "run_trace_events"

    run_id: Mapped[str] = mapped_column(ForeignKey("workflow_runs.id", ondelete="CASCADE"))
    sequence_number: Mapped[int] = mapped_column(default=1)
    step_key: Mapped[str] = mapped_column(String(120))
    title: Mapped[str] = mapped_column(String(255))
    message: Mapped[str] = mapped_column(Text)
    level: Mapped[str] = mapped_column(String(40), default="info")

    run: Mapped[WorkflowRunRecord] = relationship(back_populates="trace_events")


class ReportBundleRecord(TenantScopedMixin, TimestampedMixin, Base):
    __tablename__ = "report_bundles"

    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"))
    run_id: Mapped[str] = mapped_column(ForeignKey("workflow_runs.id", ondelete="CASCADE"))
    bundle_kind: Mapped[str] = mapped_column(String(80))
    title: Mapped[str] = mapped_column(String(255))
    format: Mapped[str] = mapped_column(String(40), default="markdown")
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    content: Mapped[str] = mapped_column(Text)
    file_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    storage_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    sha256_digest: Mapped[str | None] = mapped_column(String(64), nullable=True)
    byte_size: Mapped[int | None] = mapped_column(nullable=True)

    run: Mapped[WorkflowRunRecord] = relationship(back_populates="report_bundles")


class RunExportPackageRecord(TenantScopedMixin, TimestampedMixin, Base):
    __tablename__ = "run_export_packages"

    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"))
    run_id: Mapped[str] = mapped_column(ForeignKey("workflow_runs.id", ondelete="CASCADE"))
    export_kind: Mapped[str] = mapped_column(String(80))
    title: Mapped[str] = mapped_column(String(255))
    format: Mapped[str] = mapped_column(String(40), default="zip")
    file_name: Mapped[str] = mapped_column(String(255))
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    requested_by: Mapped[str] = mapped_column(String(255))
    storage_path: Mapped[str] = mapped_column(String(500))
    sha256_digest: Mapped[str] = mapped_column(String(64))
    byte_size: Mapped[int] = mapped_column(default=0)
    included_files: Mapped[list[str]] = mapped_column(JSON, default=list)

    run: Mapped[WorkflowRunRecord] = relationship(back_populates="export_packages")


class WorkstreamSynthesisRecord(TenantScopedMixin, TimestampedMixin, Base):
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


TENANT_SCOPED_MODELS = (
    CaseRecord,
    DocumentArtifactRecord,
    ChunkRecord,
    EvidenceNodeRecord,
    RequestItemRecord,
    QaItemRecord,
    IssueRegisterItemRecord,
    ChecklistItemRecord,
    ApprovalDecisionRecord,
    WorkflowRunRecord,
    RunTraceEventRecord,
    ReportBundleRecord,
    RunExportPackageRecord,
    WorkstreamSynthesisRecord,
    ApiClientRecord,
    OrgRuntimeConfigRecord,
)


def _serialize_value(value):
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, list):
        return [_serialize_value(item) for item in value]
    if isinstance(value, dict):
        return {key: _serialize_value(item) for key, item in value.items()}
    return value


def _serialize_record(record, *, changed_only: bool = False) -> dict | None:
    state = inspect(record)
    data: dict[str, object] = {}
    for column in state.mapper.column_attrs:
        history = state.attrs[column.key].history
        if changed_only and not history.has_changes():
            continue
        data[column.key] = _serialize_value(getattr(record, column.key))
    return data or None


def _serialize_before_state(record) -> dict | None:
    state = inspect(record)
    data: dict[str, object] = {}
    for column in state.mapper.column_attrs:
        history = state.attrs[column.key].history
        if history.deleted:
            data[column.key] = _serialize_value(history.deleted[0])
        elif not state.transient and not state.pending:
            data[column.key] = _serialize_value(getattr(record, column.key))
    return data or None


@event.listens_for(Session, "do_orm_execute")
def _apply_org_scope(execute_state) -> None:
    if not execute_state.is_select:
        return
    if execute_state.execution_options.get("skip_org_scope", False):
        return

    org_id = execute_state.session.info.get("org_id")
    allow_cross_org = execute_state.session.info.get("allow_cross_org", False)
    if not org_id or allow_cross_org:
        return

    statement = execute_state.statement
    selected_entities = {
        description.get("entity")
        for description in getattr(statement, "column_descriptions", [])
        if description.get("entity") is not None
    }
    for model in TENANT_SCOPED_MODELS:
        if model in selected_entities:
            statement = statement.where(model.org_id == org_id)
    for model in TENANT_SCOPED_MODELS:
        statement = statement.options(
            with_loader_criteria(
                model,
                model.org_id == org_id,
                include_aliases=True,
            )
        )
    execute_state.statement = statement


@event.listens_for(Session, "before_flush")
def _record_audit_events(session: Session, flush_context, instances) -> None:
    org_id = session.info.get("org_id")

    for record in session.new:
        if isinstance(record, TenantScopedMixin) and not getattr(record, "org_id", None) and org_id:
            record.org_id = org_id

    if session.info.get("skip_audit", False):
        return

    actor_id = session.info.get("actor_id")
    actor_email = session.info.get("actor_email")
    ip_address = session.info.get("ip_address")
    request_id = session.info.get("request_id")
    pending_logs: list[AuditLogRecord] = []

    for record in session.new:
        if isinstance(record, AuditLogRecord) or not isinstance(record, Base):
            continue
        pending_logs.append(
            AuditLogRecord(
                org_id=getattr(record, "org_id", org_id),
                actor_id=actor_id,
                actor_email=actor_email,
                action="CREATE",
                resource_type=getattr(record, "__tablename__", record.__class__.__name__),
                resource_id=getattr(record, "id", None),
                before_state=None,
                after_state=_serialize_record(record),
                ip_address=ip_address,
                request_id=request_id,
                status_code=None,
            )
        )

    for record in session.dirty:
        if (
            isinstance(record, AuditLogRecord)
            or not isinstance(record, Base)
            or not session.is_modified(record, include_collections=False)
        ):
            continue
        pending_logs.append(
            AuditLogRecord(
                org_id=getattr(record, "org_id", org_id),
                actor_id=actor_id,
                actor_email=actor_email,
                action="UPDATE",
                resource_type=getattr(record, "__tablename__", record.__class__.__name__),
                resource_id=getattr(record, "id", None),
                before_state=_serialize_before_state(record),
                after_state=_serialize_record(record, changed_only=True),
                ip_address=ip_address,
                request_id=request_id,
                status_code=None,
            )
        )

    for record in session.deleted:
        if isinstance(record, AuditLogRecord) or not isinstance(record, Base):
            continue
        pending_logs.append(
            AuditLogRecord(
                org_id=getattr(record, "org_id", org_id),
                actor_id=actor_id,
                actor_email=actor_email,
                action="DELETE",
                resource_type=getattr(record, "__tablename__", record.__class__.__name__),
                resource_id=getattr(record, "id", None),
                before_state=_serialize_record(record),
                after_state=None,
                ip_address=ip_address,
                request_id=request_id,
                status_code=None,
            )
        )

    if pending_logs:
        session.info["skip_audit"] = True
        try:
            session.add_all(pending_logs)
        finally:
            session.info["skip_audit"] = False
