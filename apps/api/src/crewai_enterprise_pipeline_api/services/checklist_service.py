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

        if sector_pack == SectorPack.TECH_SAAS_SERVICES:
            template.extend(TECH_SAAS_TEMPLATE)

        return tuple(template)
