from datetime import datetime
from enum import StrEnum

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
    CHANGES_REQUESTED = "changes_requested"


class SourceAdapterCategory(StrEnum):
    UPLOADED = "uploaded"
    PUBLIC = "public"
    VENDOR = "vendor"


class StorageBackendKind(StrEnum):
    LOCAL = "local"
    S3 = "s3"


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class AppHealth(ORMModel):
    status: str
    environment: str
    version: str
    timestamp: datetime
    enabled_motion_packs: list[MotionPack]
    enabled_sector_packs: list[SectorPack]


class PlatformOverview(ORMModel):
    product_name: str
    current_phase: str
    country: str
    motion_packs: list[MotionPack]
    sector_packs: list[SectorPack]
    workstream_domains: list[WorkstreamDomain]
    severity_scale: list[FlagSeverity] = Field(
        description="The shared severity scale for issue and red-flag records."
    )


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


class ApprovalDecisionCreate(BaseModel):
    reviewer: str = Field(min_length=2, max_length=255)
    note: str | None = Field(default=None, max_length=4000)


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
    fallback_mode: str


class DocumentIngestionResult(BaseModel):
    artifact: DocumentArtifactSummary
    evidence_items_created: int
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
    generated_at: datetime
    report_status: str
    approval_state: ApprovalDecisionKind | None
    executive_summary: str
    top_issues: list[IssueRegisterItemSummary]
    open_requests: list[RequestItemSummary]
    checklist_coverage: ChecklistCoverageSummary
    next_actions: list[str]
