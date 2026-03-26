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


class SourceAdapterCategory(StrEnum):
    UPLOADED = "uploaded"
    PUBLIC = "public"
    VENDOR = "vendor"


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
    mime_type: str | None = Field(default=None, max_length=120)
    processing_status: ArtifactProcessingStatus = ArtifactProcessingStatus.RECEIVED
    storage_path: str | None = Field(default=None, max_length=500)


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


class DocumentArtifactSummary(ORMModel):
    id: str
    title: str
    source_kind: ArtifactSourceKind
    document_kind: str
    mime_type: str | None
    processing_status: ArtifactProcessingStatus
    storage_path: str | None
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


class SourceAdapterSummary(BaseModel):
    adapter_key: str
    category: SourceAdapterCategory
    title: str
    purpose: str
    supports_india: bool
    supports_live_credentials: bool
    fallback_mode: str
