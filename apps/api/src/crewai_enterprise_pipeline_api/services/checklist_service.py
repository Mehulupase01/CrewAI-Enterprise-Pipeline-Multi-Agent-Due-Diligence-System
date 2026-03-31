from __future__ import annotations

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
from crewai_enterprise_pipeline_api.services.checklist_catalog import (
    ChecklistTemplateItem,
    build_motion_pack_template,
    build_sector_pack_template,
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
        blocker_items = sum(1 for item in items if item.status == ChecklistItemStatus.BLOCKED.value)
        open_mandatory_items = sum(
            1 for item in items if item.mandatory and item.status not in COMPLETED_STATUSES
        )

        workstream_breakdown: list[WorkstreamCoverageSummary] = []
        for workstream in WorkstreamDomain:
            scoped_items = [item for item in items if item.workstream_domain == workstream.value]
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
    ):
        ordered_items = [
            *build_motion_pack_template(motion_pack),
            *build_sector_pack_template(sector_pack),
        ]
        deduped_by_key: dict[str, ChecklistTemplateItem] = {}
        for item in ordered_items:
            deduped_by_key.setdefault(item.template_key, item)
        return tuple(deduped_by_key.values())
