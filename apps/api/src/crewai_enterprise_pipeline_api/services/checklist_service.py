from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from crewai_enterprise_pipeline_api.db.models import ChecklistItemRecord
from crewai_enterprise_pipeline_api.domain.models import (
    ChecklistCoverageSummary,
    ChecklistItemStatus,
    ChecklistItemSummary,
    ChecklistSeedResult,
    MotionPack,
    SectorPack,
    WorkstreamCoverageSummary,
    WorkstreamDomain,
)
from crewai_enterprise_pipeline_api.services.case_service import CaseService


@dataclass(frozen=True)
class ChecklistTemplateItem:
    template_key: str
    title: str
    detail: str
    workstream_domain: WorkstreamDomain
    mandatory: bool = True
    evidence_required: bool = True


BUY_SIDE_BASE_TEMPLATE: tuple[ChecklistTemplateItem, ...] = (
    ChecklistTemplateItem(
        template_key="financial_qoe.audited_financials",
        title="Collect audited financial statements for the last five years",
        detail=(
            "Validate annual income statement, balance sheet, and cash flow coverage, "
            "including auditor notes and management adjustments."
        ),
        workstream_domain=WorkstreamDomain.FINANCIAL_QOE,
    ),
    ChecklistTemplateItem(
        template_key="financial_qoe.monthly_bridge",
        title="Obtain monthly revenue and margin bridge",
        detail=(
            "Reconcile monthly revenue, gross margin, deferred revenue, and churn "
            "drivers to annual reported performance."
        ),
        workstream_domain=WorkstreamDomain.FINANCIAL_QOE,
    ),
    ChecklistTemplateItem(
        template_key="legal_corporate.cap_table",
        title="Validate cap table and corporate actions",
        detail=(
            "Review share issuances, transfers, ESOP pool, shareholder rights, and "
            "board or shareholder approvals."
        ),
        workstream_domain=WorkstreamDomain.LEGAL_CORPORATE,
    ),
    ChecklistTemplateItem(
        template_key="legal_corporate.material_contracts",
        title="Review material customer, vendor, and financing contracts",
        detail=(
            "Check change-of-control clauses, termination rights, pricing protections, "
            "non-competes, and assignment restrictions."
        ),
        workstream_domain=WorkstreamDomain.LEGAL_CORPORATE,
    ),
    ChecklistTemplateItem(
        template_key="tax.notice_register",
        title="Reconcile direct and indirect tax exposures",
        detail=(
            "Collect GST, TDS, income-tax filings, notices, demands, and payment "
            "history across relevant entities and states."
        ),
        workstream_domain=WorkstreamDomain.TAX,
    ),
    ChecklistTemplateItem(
        template_key="regulatory.mca_consistency",
        title="Validate MCA and statutory filing consistency",
        detail=(
            "Confirm directors, charges, registered office data, and annual filings "
            "match management disclosures."
        ),
        workstream_domain=WorkstreamDomain.REGULATORY,
    ),
    ChecklistTemplateItem(
        template_key="forensic.related_party",
        title="Map related-party flows and promoter-linked transactions",
        detail=(
            "Trace intercompany balances, promoter entities, related-party sales or "
            "expenses, and any unusual round-tripping indicators."
        ),
        workstream_domain=WorkstreamDomain.FORENSIC_COMPLIANCE,
    ),
)


CREDIT_LENDING_BASE_TEMPLATE: tuple[ChecklistTemplateItem, ...] = (
    ChecklistTemplateItem(
        template_key="financial_qoe.borrower_statements",
        title="Collect borrower financial statements and monthly MIS",
        detail=(
            "Validate the last three to five years of financial statements, monthly MIS, "
            "budget versus actuals, and management adjustments used for underwriting."
        ),
        workstream_domain=WorkstreamDomain.FINANCIAL_QOE,
    ),
    ChecklistTemplateItem(
        template_key="financial_qoe.debt_service_capacity",
        title="Assess debt-service capacity and cash flow resilience",
        detail=(
            "Compute EBITDA to debt-service coverage, free cash flow, repayment "
            "seasonality, and downside capacity under stress scenarios."
        ),
        workstream_domain=WorkstreamDomain.FINANCIAL_QOE,
    ),
    ChecklistTemplateItem(
        template_key="financial_qoe.working_capital_behaviour",
        title="Review working-capital behaviour and collections quality",
        detail=(
            "Analyse receivables aging, inventory turns where relevant, creditor stretch, "
            "cash conversion, and concentration in collections."
        ),
        workstream_domain=WorkstreamDomain.FINANCIAL_QOE,
    ),
    ChecklistTemplateItem(
        template_key="legal_corporate.security_package",
        title="Validate security package and collateral perfection",
        detail=(
            "Review charge filings, collateral coverage, guarantee structure, perfection "
            "steps, pari-passu exposures, and enforcement dependencies."
        ),
        workstream_domain=WorkstreamDomain.LEGAL_CORPORATE,
    ),
    ChecklistTemplateItem(
        template_key="tax.compliance_borrower_status",
        title="Confirm tax and statutory compliance status",
        detail=(
            "Check GST, TDS, income-tax, PF, ESI, and other statutory compliance for "
            "signals that could impair repayment or create lender exposure."
        ),
        workstream_domain=WorkstreamDomain.TAX,
    ),
    ChecklistTemplateItem(
        template_key="regulatory.licensing_and_borrowing_constraints",
        title="Review licensing, borrowing restrictions, and regulatory triggers",
        detail=(
            "Check whether the borrower faces sectoral restrictions, consent "
            "requirements, FEMA implications, or regulatory approvals tied to financing."
        ),
        workstream_domain=WorkstreamDomain.REGULATORY,
    ),
    ChecklistTemplateItem(
        template_key="forensic.end_use_and_fund_flow",
        title="Test end-use of funds and diversion risk",
        detail=(
            "Review bank statements, related-party flows, unusual round-tripping, "
            "promoter withdrawals, and deviations from stated end-use."
        ),
        workstream_domain=WorkstreamDomain.FORENSIC_COMPLIANCE,
    ),
    ChecklistTemplateItem(
        template_key="commercial.counterparty_concentration",
        title="Assess counterparty concentration and renewal dependence",
        detail=(
            "Measure customer, dealer, distributor, or platform concentration that could "
            "impair collections and repayment continuity."
        ),
        workstream_domain=WorkstreamDomain.COMMERCIAL,
    ),
)


VENDOR_ONBOARDING_BASE_TEMPLATE: tuple[ChecklistTemplateItem, ...] = (
    ChecklistTemplateItem(
        template_key="legal_corporate.vendor_registration",
        title="Validate vendor registration, ownership, and contracting authority",
        detail=(
            "Confirm incorporation details, beneficial ownership, contracting authority, "
            "and whether any material corporate changes are pending."
        ),
        workstream_domain=WorkstreamDomain.LEGAL_CORPORATE,
    ),
    ChecklistTemplateItem(
        template_key="legal_corporate.contractual_risk",
        title="Review contracting model, liability caps, and subcontracting rights",
        detail=(
            "Check standard terms, limitation of liability, indemnities, confidentiality, "
            "termination rights, and subcontracting permissions."
        ),
        workstream_domain=WorkstreamDomain.LEGAL_CORPORATE,
    ),
    ChecklistTemplateItem(
        template_key="tax.vendor_statutory_profile",
        title="Confirm GST, PAN, and statutory compliance standing",
        detail=(
            "Validate GST registration, return filing posture, withholding-tax readiness, "
            "and whether open statutory defaults could impair onboarding."
        ),
        workstream_domain=WorkstreamDomain.TAX,
    ),
    ChecklistTemplateItem(
        template_key="regulatory.vendor_restrictions",
        title="Screen regulatory restrictions, sanctions, and licensing triggers",
        detail=(
            "Check whether the vendor or its principals face sanctions, licensing gaps, "
            "watchlist alerts, or sector-specific onboarding restrictions."
        ),
        workstream_domain=WorkstreamDomain.REGULATORY,
    ),
    ChecklistTemplateItem(
        template_key="cyber_privacy.vendor_security_posture",
        title="Assess cyber, privacy, and access-control posture",
        detail=(
            "Review security controls, data-handling obligations, incident history, "
            "sub-processor use, and privacy commitments relevant to onboarding."
        ),
        workstream_domain=WorkstreamDomain.CYBER_PRIVACY,
    ),
    ChecklistTemplateItem(
        template_key="forensic.third_party_integrity",
        title="Review third-party integrity and anti-bribery risk",
        detail=(
            "Check integrity red flags, beneficial-owner concerns, conflicts of interest, "
            "anti-bribery controls, and whistleblower or misconduct signals."
        ),
        workstream_domain=WorkstreamDomain.FORENSIC_COMPLIANCE,
    ),
    ChecklistTemplateItem(
        template_key="operations.service_continuity",
        title="Test operational resilience and dependency concentration",
        detail=(
            "Review delivery resilience, key-person dependence, single-location exposure, "
            "and any concentration that could disrupt service continuity."
        ),
        workstream_domain=WorkstreamDomain.OPERATIONS,
    ),
)


TECH_SAAS_TEMPLATE: tuple[ChecklistTemplateItem, ...] = (
    ChecklistTemplateItem(
        template_key="commercial.customer_concentration",
        title="Assess customer concentration and retention quality",
        detail=(
            "Measure top-customer dependence, renewal terms, cohort retention, churn, "
            "and upsell concentration."
        ),
        workstream_domain=WorkstreamDomain.COMMERCIAL,
    ),
    ChecklistTemplateItem(
        template_key="cyber.privacy_controls",
        title="Assess data privacy and security controls",
        detail=(
            "Review security policies, incidents, access controls, processor contracts, "
            "and DPDP preparedness."
        ),
        workstream_domain=WorkstreamDomain.CYBER_PRIVACY,
    ),
    ChecklistTemplateItem(
        template_key="operations.delivery_model",
        title="Validate delivery concentration and operational dependencies",
        detail=(
            "Check key personnel dependence, implementation bottlenecks, and cloud or "
            "outsourcing dependencies."
        ),
        workstream_domain=WorkstreamDomain.OPERATIONS,
    ),
)


MANUFACTURING_INDUSTRIALS_TEMPLATE: tuple[ChecklistTemplateItem, ...] = (
    ChecklistTemplateItem(
        template_key="financial_qoe.inventory_quality",
        title="Assess inventory quality, aging, and scrap exposure",
        detail=(
            "Review raw material, WIP, and finished-goods aging, obsolete stock, "
            "scrap write-offs, and standard-cost versus actual-margin leakage."
        ),
        workstream_domain=WorkstreamDomain.FINANCIAL_QOE,
    ),
    ChecklistTemplateItem(
        template_key="operations.plant_capacity_utilisation",
        title="Validate plant capacity, utilisation, and maintenance resilience",
        detail=(
            "Review plant capacity, OEE or utilisation, unplanned downtime, "
            "maintenance backlog, and dependence on a single site or line."
        ),
        workstream_domain=WorkstreamDomain.OPERATIONS,
    ),
    ChecklistTemplateItem(
        template_key="operations.supplier_concentration",
        title="Assess supplier concentration and raw-material continuity",
        detail=(
            "Measure single-source supplier dependence, raw-material volatility, "
            "import dependencies, and continuity planning for key inputs."
        ),
        workstream_domain=WorkstreamDomain.OPERATIONS,
    ),
    ChecklistTemplateItem(
        template_key="regulatory.ehs_factory_compliance",
        title="Review factory, environmental, and EHS compliance",
        detail=(
            "Validate factory licences, consent-to-operate status, hazardous-waste "
            "controls, pollution control obligations, and major accident history."
        ),
        workstream_domain=WorkstreamDomain.REGULATORY,
    ),
    ChecklistTemplateItem(
        template_key="commercial.orderbook_channel_mix",
        title="Review order book, dealer mix, and channel concentration",
        detail=(
            "Assess order-book quality, customer and dealer concentration, export "
            "dependence, cancellation trends, and pricing pass-through ability."
        ),
        workstream_domain=WorkstreamDomain.COMMERCIAL,
    ),
    ChecklistTemplateItem(
        template_key="forensic.procurement_related_party",
        title="Trace procurement leakages and related-party vendor exposure",
        detail=(
            "Check related-party procurement, unusual vendor pricing, round-tripped "
            "purchases, and capex flows linked to promoter entities."
        ),
        workstream_domain=WorkstreamDomain.FORENSIC_COMPLIANCE,
    ),
)


BFSI_NBFC_TEMPLATE: tuple[ChecklistTemplateItem, ...] = (
    ChecklistTemplateItem(
        template_key="financial_qoe.asset_quality_and_provisioning",
        title="Review asset quality, stage migration, and provisioning adequacy",
        detail=(
            "Assess GNPA or NNPA trends, stage migration, write-offs, restructures, "
            "and provisioning adequacy across key borrower cohorts and products."
        ),
        workstream_domain=WorkstreamDomain.FINANCIAL_QOE,
    ),
    ChecklistTemplateItem(
        template_key="financial_qoe.alm_liquidity_profile",
        title="Assess ALM, liquidity buffers, and borrowing concentration",
        detail=(
            "Review maturity mismatches, liquidity buffers, funding concentration, "
            "asset-liability gaps, and refinancing dependence under stress."
        ),
        workstream_domain=WorkstreamDomain.FINANCIAL_QOE,
    ),
    ChecklistTemplateItem(
        template_key="regulatory.rbi_registration_and_returns",
        title="Validate RBI registration, product perimeter, and regulatory returns",
        detail=(
            "Confirm registration status, product or licence perimeter, supervisory "
            "history, and completeness of required RBI or statutory returns."
        ),
        workstream_domain=WorkstreamDomain.REGULATORY,
    ),
    ChecklistTemplateItem(
        template_key="operations.underwriting_and_collections_governance",
        title="Review underwriting exceptions and collections governance",
        detail=(
            "Assess policy exceptions, scorecard overrides, collections conduct, "
            "outsourced collections oversight, and grievance escalation controls."
        ),
        workstream_domain=WorkstreamDomain.OPERATIONS,
    ),
    ChecklistTemplateItem(
        template_key="cyber_privacy.kyc_aml_and_data_controls",
        title="Assess KYC, AML-monitoring, and customer-data controls",
        detail=(
            "Review onboarding controls, CKYC or KYC hygiene, AML monitoring, "
            "customer consent handling, and privileged access over borrower data."
        ),
        workstream_domain=WorkstreamDomain.CYBER_PRIVACY,
    ),
    ChecklistTemplateItem(
        template_key="forensic.connected_lending_and_evergreening",
        title="Test connected lending, evergreening, and unusual fund flows",
        detail=(
            "Trace connected lending, loan evergreening indicators, related-party "
            "exposure, rollovers, and round-tripped fund movements."
        ),
        workstream_domain=WorkstreamDomain.FORENSIC_COMPLIANCE,
    ),
)


COMPLETED_STATUSES = {
    ChecklistItemStatus.SATISFIED.value,
    ChecklistItemStatus.NOT_APPLICABLE.value,
}


class ChecklistService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.case_service = CaseService(session)

    async def seed_case_checklist(self, case_id: str) -> ChecklistSeedResult | None:
        case = await self.case_service._get_case_record(case_id)
        if case is None:
            return None

        template = self._build_template(
            MotionPack(case.motion_pack),
            SectorPack(case.sector_pack),
        )
        existing_keys = {
            item.template_key for item in case.checklist_items if item.template_key is not None
        }

        created_records: list[ChecklistItemRecord] = []
        reused_count = 0
        for item in template:
            if item.template_key in existing_keys:
                reused_count += 1
                continue
            created_records.append(
                ChecklistItemRecord(
                    case_id=case_id,
                    template_key=item.template_key,
                    title=item.title,
                    detail=item.detail,
                    workstream_domain=item.workstream_domain.value,
                    mandatory=item.mandatory,
                    evidence_required=item.evidence_required,
                    status=ChecklistItemStatus.PENDING.value,
                )
            )

        if created_records:
            self.session.add_all(created_records)
            await self.session.commit()

        result = await self.session.execute(
            select(ChecklistItemRecord)
            .where(ChecklistItemRecord.case_id == case_id)
            .order_by(ChecklistItemRecord.created_at)
        )
        checklist_items = [
            ChecklistItemSummary.model_validate(item) for item in result.scalars().all()
        ]
        return ChecklistSeedResult(
            created_count=len(created_records),
            reused_count=reused_count,
            checklist_items=checklist_items,
        )

    async def get_coverage_summary(
        self,
        case_id: str,
    ) -> ChecklistCoverageSummary | None:
        case = await self.case_service._get_case_record(case_id)
        if case is None:
            return None

        items = case.checklist_items
        total_items = len(items)
        mandatory_items = sum(1 for item in items if item.mandatory)
        completed_items = sum(1 for item in items if item.status in COMPLETED_STATUSES)
        blocker_items = sum(
            1 for item in items if item.status == ChecklistItemStatus.BLOCKED.value
        )
        open_mandatory_items = sum(
            1
            for item in items
            if item.mandatory and item.status not in COMPLETED_STATUSES
        )

        workstream_breakdown: list[WorkstreamCoverageSummary] = []
        for workstream in WorkstreamDomain:
            scoped_items = [
                item for item in items if item.workstream_domain == workstream.value
            ]
            if not scoped_items:
                continue
            workstream_breakdown.append(
                WorkstreamCoverageSummary(
                    workstream_domain=workstream,
                    total_items=len(scoped_items),
                    completed_items=sum(
                        1 for item in scoped_items if item.status in COMPLETED_STATUSES
                    ),
                    blocker_items=sum(
                        1
                        for item in scoped_items
                        if item.status == ChecklistItemStatus.BLOCKED.value
                    ),
                )
            )

        return ChecklistCoverageSummary(
            total_items=total_items,
            mandatory_items=mandatory_items,
            completed_items=completed_items,
            blocker_items=blocker_items,
            open_mandatory_items=open_mandatory_items,
            completion_ready=open_mandatory_items == 0 and blocker_items == 0,
            workstream_breakdown=workstream_breakdown,
        )

    async def get_checklist_item(
        self,
        case_id: str,
        item_id: str,
    ) -> ChecklistItemSummary | None:
        result = await self.session.execute(
            select(ChecklistItemRecord).where(
                ChecklistItemRecord.id == item_id,
                ChecklistItemRecord.case_id == case_id,
            )
        )
        record = result.scalar_one_or_none()
        if record is None:
            return None
        return ChecklistItemSummary.model_validate(record)

    def _build_template(
        self,
        motion_pack: MotionPack,
        sector_pack: SectorPack,
    ) -> tuple[ChecklistTemplateItem, ...]:
        template: list[ChecklistTemplateItem] = []

        if motion_pack == MotionPack.BUY_SIDE_DILIGENCE:
            template.extend(BUY_SIDE_BASE_TEMPLATE)
        elif motion_pack == MotionPack.CREDIT_LENDING:
            template.extend(CREDIT_LENDING_BASE_TEMPLATE)
        elif motion_pack == MotionPack.VENDOR_ONBOARDING:
            template.extend(VENDOR_ONBOARDING_BASE_TEMPLATE)

        if sector_pack == SectorPack.TECH_SAAS_SERVICES:
            template.extend(TECH_SAAS_TEMPLATE)
        elif sector_pack == SectorPack.MANUFACTURING_INDUSTRIALS:
            template.extend(MANUFACTURING_INDUSTRIALS_TEMPLATE)
        elif sector_pack == SectorPack.BFSI_NBFC:
            template.extend(BFSI_NBFC_TEMPLATE)

        return tuple(template)
