from datetime import date, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class MotionPack(StrEnum):
    BUY_SIDE_DILIGENCE = "buy_side_diligence"
    CREDIT_LENDING = "credit_lending"
    VENDOR_ONBOARDING = "vendor_onboarding"


class SectorPack(StrEnum):
    TECH_SAAS_SERVICES = "tech_saas_services"
    MANUFACTURING_INDUSTRIALS = "manufacturing_industrials"
    BFSI_NBFC = "bfsi_nbfc"


class WorkstreamDomain(StrEnum):
    FINANCIAL_QOE = "financial_qoe"
    LEGAL_CORPORATE = "legal_corporate"
    TAX = "tax"
    REGULATORY = "regulatory"
    COMMERCIAL = "commercial"
    HR = "hr"
    CYBER_PRIVACY = "cyber_privacy"
    OPERATIONS = "operations"
    FORENSIC_COMPLIANCE = "forensic_compliance"


class FlagSeverity(StrEnum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class CaseStatus(StrEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    IN_REVIEW = "in_review"
    COMPLETE = "complete"


class ArtifactSourceKind(StrEnum):
    UPLOADED_DATAROOM = "uploaded_dataroom"
    PUBLIC_REGISTRY = "public_registry"
    LISTED_DISCLOSURE = "listed_disclosure"
    WEB_RESEARCH = "web_research"
    VENDOR_CONNECTOR = "vendor_connector"
    MANAGEMENT_RESPONSE = "management_response"


class ArtifactProcessingStatus(StrEnum):
    RECEIVED = "received"
    STAGED = "staged"
    PARSED = "parsed"
    VERIFIED = "verified"


class EvidenceKind(StrEnum):
    FACT = "fact"
    METRIC = "metric"
    RISK = "risk"
    CONTRACT = "contract"
    GOVERNANCE = "governance"


class RequestItemStatus(StrEnum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RECEIVED = "received"
    CLOSED = "closed"
    BLOCKED = "blocked"


class QaItemStatus(StrEnum):
    OPEN = "open"
    ANSWERED = "answered"
    ESCALATED = "escalated"
    CLOSED = "closed"


class IssueStatus(StrEnum):
    OPEN = "open"
    IN_REVIEW = "in_review"
    MITIGATION_PLANNED = "mitigation_planned"
    CLOSED = "closed"
    ACCEPTED = "accepted"


class ChecklistItemStatus(StrEnum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SATISFIED = "satisfied"
    BLOCKED = "blocked"
    NOT_APPLICABLE = "not_applicable"


class ApprovalDecisionKind(StrEnum):
    APPROVED = "approved"
    REJECTED = "rejected"
    CONDITIONALLY_APPROVED = "conditionally_approved"
    CHANGES_REQUESTED = "changes_requested"


class WorkflowRunStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class RunEventLevel(StrEnum):
    INFO = "info"
    WARNING = "warning"


class ReportBundleKind(StrEnum):
    EXECUTIVE_MEMO_MARKDOWN = "executive_memo_markdown"
    ISSUE_REGISTER_MARKDOWN = "issue_register_markdown"
    WORKSTREAM_SYNTHESIS_MARKDOWN = "workstream_synthesis_markdown"
    FULL_REPORT_MARKDOWN = "full_report_markdown"
    FINANCIAL_ANNEX_MARKDOWN = "financial_annex_markdown"
    FULL_REPORT_DOCX = "full_report_docx"
    FULL_REPORT_PDF = "full_report_pdf"


class ReportTemplateKind(StrEnum):
    STANDARD = "standard"
    LENDER = "lender"
    BOARD_MEMO = "board_memo"
    ONE_PAGER = "one_pager"


class RunExportPackageKind(StrEnum):
    RUN_REPORT_ARCHIVE = "run_report_archive"


class WorkstreamSynthesisStatus(StrEnum):
    READY_FOR_REVIEW = "ready_for_review"
    NEEDS_FOLLOW_UP = "needs_follow_up"
    BLOCKED = "blocked"


class SourceAdapterCategory(StrEnum):
    UPLOADED = "uploaded"
    PUBLIC = "public"
    VENDOR = "vendor"


class SourceAdapterStatus(StrEnum):
    AVAILABLE = "available"
    STUB = "stub"
    UNAVAILABLE = "unavailable"


class StorageBackendKind(StrEnum):
    LOCAL = "local"
    S3 = "s3"


class UserRole(StrEnum):
    VIEWER = "viewer"
    ANALYST = "analyst"
    REVIEWER = "reviewer"
    ADMIN = "admin"


class LlmProviderKind(StrEnum):
    NONE = "none"
    OPENROUTER = "openrouter"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"


class DependencyCategory(StrEnum):
    INFRA = "infra"
    LLM = "llm"
    REGISTRY = "registry"
    VENDOR = "vendor"
    FEED = "feed"


class DependencyMode(StrEnum):
    LIVE = "live"
    STUB = "stub"
    UNCONFIGURED = "unconfigured"
    DISABLED = "disabled"


class DependencyState(StrEnum):
    OK = "ok"
    DEGRADED = "degraded"
    FAILED = "failed"


class ComplianceStatus(StrEnum):
    COMPLIANT = "compliant"
    NON_COMPLIANT = "non_compliant"
    PARTIALLY_COMPLIANT = "partially_compliant"
    UNKNOWN = "unknown"


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class AppHealth(ORMModel):
    status: str
    environment: str
    version: str
    timestamp: datetime
    auth_required: bool
    default_actor_role: UserRole
    request_id_header_name: str
    enabled_motion_packs: list[MotionPack]
    enabled_sector_packs: list[SectorPack]


class LivenessReport(BaseModel):
    status: str
    environment: str
    timestamp: datetime


class PlatformOverview(ORMModel):
    product_name: str
    current_phase: str
    country: str
    auth_required: bool
    motion_packs: list[MotionPack]
    sector_packs: list[SectorPack]
    workstream_domains: list[WorkstreamDomain]
    severity_scale: list[FlagSeverity] = Field(
        description="The shared severity scale for issue and red-flag records."
    )


class AuthenticatedPrincipal(BaseModel):
    user_id: str
    name: str
    email: str
    role: UserRole
    org_id: str
    auth_required: bool


class TokenRequest(BaseModel):
    client_id: str = Field(min_length=3, max_length=120)
    client_secret: str = Field(min_length=8, max_length=255)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    actor_id: str
    actor_email: str
    org_id: str
    role: UserRole


class AuditLogEntry(ORMModel):
    id: str
    org_id: str | None
    actor_id: str | None
    actor_email: str | None
    action: str
    resource_type: str
    resource_id: str | None
    before_state: dict[str, Any] | None
    after_state: dict[str, Any] | None
    ip_address: str | None
    request_id: str | None
    status_code: int | None
    created_at: datetime
    updated_at: datetime


class AuditLogListResponse(BaseModel):
    total: int
    items: list[AuditLogEntry] = Field(default_factory=list)


class ReadinessComponent(BaseModel):
    name: str
    status: str
    detail: str


class DependencyStatusEntry(BaseModel):
    name: str
    category: DependencyCategory
    mode: DependencyMode
    status: DependencyState
    detail: str
    latency_ms: float = Field(ge=0.0)
    last_checked_at: datetime
    last_success_at: datetime | None = None
    failure_reason: str | None = None


class DependencyStatusReport(BaseModel):
    status: str
    environment: str
    timestamp: datetime
    auth_required: bool
    dependencies: list[DependencyStatusEntry]


class LlmModelOption(BaseModel):
    model_id: str
    label: str
    provider: str
    tool_calling_supported: bool = True
    text_output_supported: bool = True
    context_length: int | None = None
    pricing_summary: str | None = None


class LlmProviderSummary(BaseModel):
    provider: str
    label: str
    configured: bool
    available: bool
    detail: str
    models: list[LlmModelOption] = Field(default_factory=list)


class OrgLlmRuntimeConfig(ORMModel):
    org_id: str
    llm_provider: str | None = None
    llm_model: str | None = None
    updated_at: datetime | None = None


class OrgLlmRuntimeConfigUpdate(BaseModel):
    llm_provider: str | None = None
    llm_model: str | None = None


class QualityScorecard(BaseModel):
    completeness: float = Field(ge=0.0, le=1.0)
    accuracy: float = Field(ge=0.0, le=1.0)
    hallucination_rate: float = Field(ge=0.0, le=1.0)
    citation_coverage: float = Field(ge=0.0, le=1.0)
    overall_score: float = Field(ge=0.0, le=1.0)


class ReadinessReport(BaseModel):
    status: str
    environment: str
    timestamp: datetime
    auth_required: bool
    components: list[ReadinessComponent]


class CaseCreate(BaseModel):
    name: str = Field(min_length=3, max_length=255)
    target_name: str = Field(min_length=2, max_length=255)
    summary: str | None = Field(default=None, max_length=4000)
    motion_pack: MotionPack = MotionPack.BUY_SIDE_DILIGENCE
    sector_pack: SectorPack = SectorPack.TECH_SAAS_SERVICES
    country: str = "India"


class DocumentArtifactCreate(BaseModel):
    title: str = Field(min_length=2, max_length=255)
    source_kind: ArtifactSourceKind
    document_kind: str = Field(min_length=2, max_length=120)
    original_filename: str | None = Field(default=None, max_length=255)
    mime_type: str | None = Field(default=None, max_length=120)
    processing_status: ArtifactProcessingStatus = ArtifactProcessingStatus.RECEIVED
    storage_path: str | None = Field(default=None, max_length=500)
    parser_name: str | None = Field(default=None, max_length=80)
    sha256_digest: str | None = Field(default=None, max_length=64)
    byte_size: int | None = Field(default=None, ge=0)


class EvidenceItemCreate(BaseModel):
    title: str = Field(min_length=2, max_length=255)
    evidence_kind: EvidenceKind
    workstream_domain: WorkstreamDomain
    citation: str = Field(min_length=2, max_length=500)
    excerpt: str = Field(min_length=3, max_length=8000)
    artifact_id: str | None = None
    confidence: float = Field(default=0.7, ge=0.0, le=1.0)


class RequestItemCreate(BaseModel):
    title: str = Field(min_length=2, max_length=255)
    detail: str = Field(min_length=3, max_length=4000)
    owner: str | None = Field(default=None, max_length=255)
    status: RequestItemStatus = RequestItemStatus.OPEN


class QaItemCreate(BaseModel):
    question: str = Field(min_length=3, max_length=4000)
    requested_by: str | None = Field(default=None, max_length=255)
    response: str | None = Field(default=None, max_length=4000)
    status: QaItemStatus = QaItemStatus.OPEN


class IssueRegisterItemCreate(BaseModel):
    title: str = Field(min_length=2, max_length=255)
    summary: str = Field(min_length=3, max_length=4000)
    severity: FlagSeverity
    workstream_domain: WorkstreamDomain
    business_impact: str = Field(min_length=3, max_length=4000)
    recommended_action: str | None = Field(default=None, max_length=4000)
    source_evidence_id: str | None = None
    confidence: float = Field(default=0.75, ge=0.0, le=1.0)
    status: IssueStatus = IssueStatus.OPEN


class ChecklistItemCreate(BaseModel):
    title: str = Field(min_length=2, max_length=255)
    detail: str = Field(min_length=3, max_length=4000)
    workstream_domain: WorkstreamDomain
    mandatory: bool = True
    evidence_required: bool = True
    owner: str | None = Field(default=None, max_length=255)
    note: str | None = Field(default=None, max_length=4000)
    template_key: str | None = Field(default=None, max_length=255)
    status: ChecklistItemStatus = ChecklistItemStatus.PENDING


class ChecklistItemUpdate(BaseModel):
    status: ChecklistItemStatus | None = None
    owner: str | None = Field(default=None, max_length=255)
    note: str | None = Field(default=None, max_length=4000)


class CaseUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=3, max_length=255)
    summary: str | None = Field(default=None, max_length=4000)
    status: CaseStatus | None = None
    sector_pack: SectorPack | None = None


class IssueUpdate(BaseModel):
    status: IssueStatus | None = None
    severity: FlagSeverity | None = None
    summary: str | None = Field(default=None, max_length=4000)
    recommended_action: str | None = Field(default=None, max_length=4000)


class RequestItemUpdate(BaseModel):
    status: RequestItemStatus | None = None
    owner: str | None = Field(default=None, max_length=255)
    detail: str | None = Field(default=None, max_length=4000)


class QaItemUpdate(BaseModel):
    response: str | None = Field(default=None, max_length=4000)
    status: QaItemStatus | None = None


class EvidenceItemUpdate(BaseModel):
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    title: str | None = Field(default=None, min_length=2, max_length=255)
    excerpt: str | None = Field(default=None, min_length=3, max_length=8000)


class ApprovalDecisionCreate(BaseModel):
    reviewer: str = Field(min_length=2, max_length=255)
    note: str | None = Field(default=None, max_length=4000)
    decision: ApprovalDecisionKind | None = None


class WorkflowRunCreate(BaseModel):
    requested_by: str = Field(default="Operator", min_length=2, max_length=255)
    note: str | None = Field(default=None, max_length=4000)
    report_template: ReportTemplateKind = ReportTemplateKind.STANDARD
    llm_provider_override: str | None = Field(default=None, max_length=80)
    llm_model_override: str | None = Field(default=None, max_length=255)


class SourceAdapterFetchRequest(BaseModel):
    identifier: str = Field(min_length=2, max_length=255)
    params: dict[str, Any] = Field(default_factory=dict)


class RunExportPackageCreate(BaseModel):
    requested_by: str = Field(default="Operator", min_length=2, max_length=255)
    title: str | None = Field(default=None, max_length=255)
    include_json_snapshot: bool = True


class DocumentArtifactSummary(ORMModel):
    id: str
    title: str
    original_filename: str | None
    source_kind: ArtifactSourceKind
    document_kind: str
    mime_type: str | None
    processing_status: ArtifactProcessingStatus
    storage_path: str | None
    parser_name: str | None
    sha256_digest: str | None
    byte_size: int | None
    created_at: datetime
    updated_at: datetime


class EvidenceItemSummary(ORMModel):
    id: str
    title: str
    evidence_kind: EvidenceKind
    workstream_domain: WorkstreamDomain
    citation: str
    excerpt: str
    artifact_id: str | None
    confidence: float
    created_at: datetime
    updated_at: datetime


class RequestItemSummary(ORMModel):
    id: str
    title: str
    detail: str
    owner: str | None
    status: RequestItemStatus
    created_at: datetime
    updated_at: datetime


class QaItemSummary(ORMModel):
    id: str
    question: str
    requested_by: str | None
    response: str | None
    status: QaItemStatus
    created_at: datetime
    updated_at: datetime


class IssueRegisterItemSummary(ORMModel):
    id: str
    title: str
    summary: str
    severity: FlagSeverity
    status: IssueStatus
    workstream_domain: WorkstreamDomain
    business_impact: str
    recommended_action: str | None
    source_evidence_id: str | None
    confidence: float
    created_at: datetime
    updated_at: datetime


class ChecklistItemSummary(ORMModel):
    id: str
    title: str
    detail: str
    workstream_domain: WorkstreamDomain
    mandatory: bool
    evidence_required: bool
    owner: str | None
    note: str | None
    template_key: str | None
    status: ChecklistItemStatus
    created_at: datetime
    updated_at: datetime


class WorkstreamCoverageSummary(BaseModel):
    workstream_domain: WorkstreamDomain
    total_items: int
    completed_items: int
    blocker_items: int


class ChecklistCoverageSummary(BaseModel):
    total_items: int
    mandatory_items: int
    completed_items: int
    blocker_items: int
    open_mandatory_items: int
    completion_ready: bool
    workstream_breakdown: list[WorkstreamCoverageSummary]


class ChecklistAutoUpdate(BaseModel):
    checklist_id: str
    template_key: str
    status: ChecklistItemStatus
    note: str


class ApprovalDecisionSummary(ORMModel):
    id: str
    reviewer: str
    note: str | None
    decision: ApprovalDecisionKind
    rationale: str
    ready_for_export: bool
    open_mandatory_items: int
    blocking_issue_count: int
    created_at: datetime
    updated_at: datetime


class ReportBundleSummary(ORMModel):
    id: str
    run_id: str
    bundle_kind: ReportBundleKind
    title: str
    format: str
    summary: str | None
    content: str
    file_name: str | None = None
    storage_path: str | None = None
    sha256_digest: str | None = None
    byte_size: int | None = None
    created_at: datetime
    updated_at: datetime


class RunExportPackageSummary(ORMModel):
    id: str
    case_id: str
    run_id: str
    export_kind: RunExportPackageKind
    title: str
    format: str
    file_name: str
    summary: str | None
    requested_by: str
    storage_path: str
    sha256_digest: str
    byte_size: int
    included_files: list[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class RunTraceEventSummary(ORMModel):
    id: str
    run_id: str
    sequence_number: int
    step_key: str
    title: str
    message: str
    level: RunEventLevel
    created_at: datetime
    updated_at: datetime


class WorkflowRunSummary(ORMModel):
    id: str
    case_id: str
    requested_by: str
    note: str | None
    report_template: ReportTemplateKind
    effective_llm_provider: str | None = None
    effective_llm_model: str | None = None
    status: WorkflowRunStatus
    summary: str | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class WorkstreamSynthesisSummary(ORMModel):
    id: str
    run_id: str
    workstream_domain: WorkstreamDomain
    status: WorkstreamSynthesisStatus
    headline: str
    narrative: str
    finding_count: int
    blocker_count: int
    confidence: float
    recommended_next_action: str
    created_at: datetime
    updated_at: datetime


class WorkflowRunDetail(WorkflowRunSummary):
    trace_events: list[RunTraceEventSummary] = Field(default_factory=list)
    report_bundles: list[ReportBundleSummary] = Field(default_factory=list)
    export_packages: list[RunExportPackageSummary] = Field(default_factory=list)
    workstream_syntheses: list[WorkstreamSynthesisSummary] = Field(default_factory=list)


class CaseSummary(ORMModel):
    id: str
    name: str
    target_name: str
    country: str
    summary: str | None
    motion_pack: MotionPack
    sector_pack: SectorPack
    status: CaseStatus
    created_at: datetime
    updated_at: datetime


class CaseDetail(CaseSummary):
    documents: list[DocumentArtifactSummary] = Field(default_factory=list)
    evidence_items: list[EvidenceItemSummary] = Field(default_factory=list)
    request_items: list[RequestItemSummary] = Field(default_factory=list)
    qa_items: list[QaItemSummary] = Field(default_factory=list)
    issues: list[IssueRegisterItemSummary] = Field(default_factory=list)
    checklist_items: list[ChecklistItemSummary] = Field(default_factory=list)
    approvals: list[ApprovalDecisionSummary] = Field(default_factory=list)


class SourceAdapterSummary(BaseModel):
    adapter_key: str
    category: SourceAdapterCategory
    title: str
    purpose: str
    supports_india: bool
    supports_live_credentials: bool
    requires_api_key: bool = False
    status: SourceAdapterStatus = SourceAdapterStatus.AVAILABLE
    supports_fetch: bool = True
    identifier_label: str | None = None
    source_kind: ArtifactSourceKind | None = None
    default_document_kind: str | None = None
    default_workstream_domain: WorkstreamDomain | None = None
    fallback_mode: str


class ChunkSummary(ORMModel):
    id: str
    chunk_index: int
    section_title: str | None
    text: str
    page_number: int | None
    char_start: int
    char_end: int
    has_embedding: bool
    created_at: datetime
    updated_at: datetime


class DocumentIngestionResult(BaseModel):
    artifact: DocumentArtifactSummary
    evidence_items_created: int
    chunks_created: int = 0
    entities_extracted: int = 0
    extracted_character_count: int
    parser_name: str
    storage_backend: StorageBackendKind


class IssueScanResult(BaseModel):
    created_count: int
    reused_count: int
    issues: list[IssueRegisterItemSummary]


class ChecklistSeedResult(BaseModel):
    created_count: int
    reused_count: int
    checklist_items: list[ChecklistItemSummary]


class ExecutiveMemoReport(BaseModel):
    case_id: str
    case_name: str
    target_name: str
    motion_pack: MotionPack
    sector_pack: SectorPack
    report_title: str
    generated_at: datetime
    report_status: str
    approval_state: ApprovalDecisionKind | None
    executive_summary: str
    top_issues: list[IssueRegisterItemSummary]
    open_requests: list[RequestItemSummary]
    checklist_coverage: ChecklistCoverageSummary
    motion_pack_highlights: list[str] = Field(default_factory=list)
    sector_pack_highlights: list[str] = Field(default_factory=list)
    next_actions: list[str]


class ValuationBridgeItem(BaseModel):
    label: str
    category: str
    amount: float | None = None
    impact: str
    evidence_ids: list[str] = Field(default_factory=list)


class SpaIssueItem(BaseModel):
    title: str
    severity: FlagSeverity
    rationale: str
    recommendation: str
    evidence_ids: list[str] = Field(default_factory=list)


class PmiRiskItem(BaseModel):
    area: str
    severity: FlagSeverity
    description: str
    day_one_action: str
    evidence_ids: list[str] = Field(default_factory=list)


class BuySideAnalysis(BaseModel):
    case_id: str
    valuation_bridge: list[ValuationBridgeItem] = Field(default_factory=list)
    spa_issues: list[SpaIssueItem] = Field(default_factory=list)
    pmi_risks: list[PmiRiskItem] = Field(default_factory=list)
    flags: list[str] = Field(default_factory=list)
    checklist_updates: list[ChecklistAutoUpdate] = Field(default_factory=list)


class BorrowerScoreSection(BaseModel):
    score: int = Field(ge=0, le=100)
    rating: str
    rationale: str
    flags: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)


class CovenantTrackingItem(BaseModel):
    name: str
    status: str
    threshold: str | None = None
    current_value: str | None = None
    note: str
    evidence_ids: list[str] = Field(default_factory=list)


class BorrowerScorecard(BaseModel):
    case_id: str
    financial_health: BorrowerScoreSection
    collateral: BorrowerScoreSection
    covenants: BorrowerScoreSection
    overall_score: int = Field(ge=0, le=100)
    overall_rating: str
    covenant_tracking: list[CovenantTrackingItem] = Field(default_factory=list)
    checklist_updates: list[ChecklistAutoUpdate] = Field(default_factory=list)


class VendorScoreBreakdownItem(BaseModel):
    factor: str
    score: int = Field(ge=0, le=100)
    weight: float = Field(ge=0.0, le=1.0)
    rationale: str
    evidence_ids: list[str] = Field(default_factory=list)


class VendorQuestionnaireItem(BaseModel):
    section: str
    status: str
    detail: str


class VendorRiskTier(BaseModel):
    case_id: str
    tier: str
    overall_score: int = Field(ge=0, le=100)
    scoring_breakdown: list[VendorScoreBreakdownItem] = Field(default_factory=list)
    questionnaire: list[VendorQuestionnaireItem] = Field(default_factory=list)
    certifications_required: list[str] = Field(default_factory=list)
    next_review_date: date
    flags: list[str] = Field(default_factory=list)
    checklist_updates: list[ChecklistAutoUpdate] = Field(default_factory=list)


class ArrWaterfallItem(BaseModel):
    label: str
    amount: float
    note: str


class TechSaasMetricsSummary(BaseModel):
    case_id: str
    arr: float | None = None
    mrr: float | None = None
    nrr: float | None = Field(default=None, ge=0.0)
    churn_rate: float | None = Field(default=None, ge=0.0, le=1.0)
    ltv: float | None = None
    cac: float | None = None
    payback_months: float | None = Field(default=None, ge=0.0)
    arr_waterfall: list[ArrWaterfallItem] = Field(default_factory=list)
    flags: list[str] = Field(default_factory=list)
    checklist_updates: list[ChecklistAutoUpdate] = Field(default_factory=list)


class AssetRegisterItem(BaseModel):
    asset_name: str
    carrying_value: float | None = None
    replacement_cost: float | None = None
    replacement_gap: float | None = None
    note: str


class ManufacturingMetricsSummary(BaseModel):
    case_id: str
    capacity_utilization: float | None = Field(default=None, ge=0.0)
    dio: float | None = Field(default=None, ge=0.0)
    dso: float | None = Field(default=None, ge=0.0)
    dpo: float | None = Field(default=None, ge=0.0)
    asset_turnover: float | None = Field(default=None, ge=0.0)
    asset_register: list[AssetRegisterItem] = Field(default_factory=list)
    flags: list[str] = Field(default_factory=list)
    checklist_updates: list[ChecklistAutoUpdate] = Field(default_factory=list)


class AlmBucketGap(BaseModel):
    bucket_label: str
    mismatch_ratio: float = Field(ge=0.0)
    note: str


class BfsiNbfcMetricsSummary(BaseModel):
    case_id: str
    gnpa: float | None = Field(default=None, ge=0.0, le=1.0)
    nnpa: float | None = Field(default=None, ge=0.0, le=1.0)
    crar: float | None = Field(default=None, ge=0.0)
    alm_mismatch: float | None = Field(default=None, ge=0.0)
    psl_compliance: ComplianceStatus = ComplianceStatus.UNKNOWN
    alm_bucket_gaps: list[AlmBucketGap] = Field(default_factory=list)
    flags: list[str] = Field(default_factory=list)
    checklist_updates: list[ChecklistAutoUpdate] = Field(default_factory=list)


class WorkflowRunResult(BaseModel):
    run: WorkflowRunDetail
    executive_memo: ExecutiveMemoReport


class WorkflowRunEnqueueResult(BaseModel):
    run_id: str
    case_id: str
    status: WorkflowRunStatus = WorkflowRunStatus.QUEUED
    message: str = "Workflow run enqueued for background processing"


class FinancialPeriod(BaseModel):
    label: str
    revenue: float | None = None
    gross_profit: float | None = None
    operating_profit: float | None = None
    ebitda: float | None = None
    pat: float | None = None
    operating_cash_flow: float | None = None
    net_debt: float | None = None
    interest_expense: float | None = None
    working_capital: float | None = None
    total_assets: float | None = None
    shareholder_equity: float | None = None
    customer_concentration_top_3: float | None = None
    q4_revenue_share: float | None = None


class QoEAdjustment(BaseModel):
    label: str
    amount: float
    category: str


class FinancialStatement(BaseModel):
    artifact_id: str | None = None
    artifact_title: str
    document_kind: str
    parser_name: str
    periods: list[FinancialPeriod] = Field(default_factory=list)
    qoe_adjustments: list[QoEAdjustment] = Field(default_factory=list)
    flags: list[str] = Field(default_factory=list)


class FinancialMetricSummary(BaseModel):
    case_id: str
    statement_count: int
    statements: list[FinancialStatement] = Field(default_factory=list)
    periods: list[FinancialPeriod] = Field(default_factory=list)
    ratios: dict[str, float | None] = Field(default_factory=dict)
    qoe_adjustments: list[QoEAdjustment] = Field(default_factory=list)
    normalized_ebitda: float | None = None
    flags: list[str] = Field(default_factory=list)
    checklist_updates: list[ChecklistAutoUpdate] = Field(default_factory=list)


class DirectorProfile(BaseModel):
    name: str | None = None
    din: str
    din_valid_format: bool
    source_artifact_id: str | None = None


class ContractClauseReview(BaseModel):
    clause_key: str
    present: bool
    note: str


class ContractReviewResult(BaseModel):
    artifact_id: str | None = None
    contract_title: str
    contract_type: str
    governing_law: str | None = None
    clauses: list[ContractClauseReview] = Field(default_factory=list)
    flags: list[str] = Field(default_factory=list)


class LegalStructureSummary(BaseModel):
    case_id: str
    artifact_count: int
    directors: list[DirectorProfile] = Field(default_factory=list)
    shareholding_summary: dict[str, float] = Field(default_factory=dict)
    charges_detected: int = 0
    subsidiary_mentions: list[str] = Field(default_factory=list)
    contract_reviews: list[ContractReviewResult] = Field(default_factory=list)
    flags: list[str] = Field(default_factory=list)
    checklist_updates: list[ChecklistAutoUpdate] = Field(default_factory=list)


class TaxComplianceItem(BaseModel):
    tax_area: str
    status: ComplianceStatus
    evidence_ids: list[str] = Field(default_factory=list)
    notes: str


class TaxComplianceSummary(BaseModel):
    case_id: str
    gstins: list[str] = Field(default_factory=list)
    items: list[TaxComplianceItem] = Field(default_factory=list)
    flags: list[str] = Field(default_factory=list)
    checklist_updates: list[ChecklistAutoUpdate] = Field(default_factory=list)


class ComplianceMatrixItem(BaseModel):
    regulation: str
    regulator: str
    status: ComplianceStatus
    evidence_ids: list[str] = Field(default_factory=list)
    notes: str


class ComplianceMatrixSummary(BaseModel):
    case_id: str
    sector_pack: SectorPack
    items: list[ComplianceMatrixItem] = Field(default_factory=list)
    flags: list[str] = Field(default_factory=list)
    checklist_updates: list[ChecklistAutoUpdate] = Field(default_factory=list)


class CommercialConcentrationSignal(BaseModel):
    subject: str
    share_of_revenue: float = Field(ge=0.0, le=1.0)
    category: str = "customer"
    note: str
    evidence_ids: list[str] = Field(default_factory=list)


class CommercialRenewalSignal(BaseModel):
    counterparty: str | None = None
    status: str
    note: str
    evidence_ids: list[str] = Field(default_factory=list)


class CommercialSummary(BaseModel):
    case_id: str
    concentration_signals: list[CommercialConcentrationSignal] = Field(default_factory=list)
    net_revenue_retention: float | None = Field(default=None, ge=0.0)
    churn_rate: float | None = Field(default=None, ge=0.0, le=1.0)
    pricing_signals: list[str] = Field(default_factory=list)
    renewal_signals: list[CommercialRenewalSignal] = Field(default_factory=list)
    flags: list[str] = Field(default_factory=list)
    checklist_updates: list[ChecklistAutoUpdate] = Field(default_factory=list)


class OperationsDependencySignal(BaseModel):
    dependency_type: str
    label: str
    detail: str
    evidence_ids: list[str] = Field(default_factory=list)


class OperationsSummary(BaseModel):
    case_id: str
    supplier_concentration_top_3: float | None = Field(default=None, ge=0.0, le=1.0)
    dependency_signals: list[OperationsDependencySignal] = Field(default_factory=list)
    single_site_dependency: bool = False
    key_person_dependencies: list[str] = Field(default_factory=list)
    flags: list[str] = Field(default_factory=list)
    checklist_updates: list[ChecklistAutoUpdate] = Field(default_factory=list)


class CyberControlCheck(BaseModel):
    control_key: str
    status: ComplianceStatus
    notes: str
    evidence_ids: list[str] = Field(default_factory=list)


class CyberPrivacySummary(BaseModel):
    case_id: str
    controls: list[CyberControlCheck] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)
    breach_history: list[str] = Field(default_factory=list)
    flags: list[str] = Field(default_factory=list)
    checklist_updates: list[ChecklistAutoUpdate] = Field(default_factory=list)


class ForensicFlagType(StrEnum):
    RELATED_PARTY = "RELATED_PARTY"
    ROUND_TRIPPING = "ROUND_TRIPPING"
    REVENUE_ANOMALY = "REVENUE_ANOMALY"
    LITIGATION = "LITIGATION"


class ForensicFlag(BaseModel):
    flag_type: ForensicFlagType
    severity: FlagSeverity
    description: str
    evidence_ids: list[str] = Field(default_factory=list)


class ForensicSummary(BaseModel):
    case_id: str
    flags: list[ForensicFlag] = Field(default_factory=list)
    checklist_updates: list[ChecklistAutoUpdate] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Evidence Intelligence (Phase 5)
# ---------------------------------------------------------------------------


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=500)
    top_k: int = Field(default=10, ge=1, le=100)
    workstream_domain: WorkstreamDomain | None = None


class EvidenceSearchResult(BaseModel):
    chunk_id: str
    artifact_id: str
    text: str
    score: float = Field(ge=0.0, le=1.0)
    section_title: str | None = None
    page_number: int | None = None


class EvidenceSearchResponse(BaseModel):
    results: list[EvidenceSearchResult]
    total: int


class ConflictType(StrEnum):
    CONTRADICTORY = "contradictory"
    DUPLICATE = "duplicate"


class EvidenceConflict(BaseModel):
    evidence_a_id: str
    evidence_b_id: str
    similarity: float = Field(ge=0.0, le=1.0)
    conflict_type: ConflictType
    explanation: str
