from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


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


class AppHealth(BaseModel):
    status: str
    environment: str
    version: str
    timestamp: datetime
    enabled_motion_packs: list[MotionPack]
    enabled_sector_packs: list[SectorPack]


class PlatformOverview(BaseModel):
    product_name: str
    current_phase: str
    country: str
    motion_packs: list[MotionPack]
    sector_packs: list[SectorPack]
    workstream_domains: list[WorkstreamDomain]
    severity_scale: list[FlagSeverity] = Field(
        description="The shared severity scale for issue and red-flag records."
    )
