from __future__ import annotations

import re

from sqlalchemy.ext.asyncio import AsyncSession

from crewai_enterprise_pipeline_api.domain.models import (
    AssetRegisterItem,
    ChecklistAutoUpdate,
    ChecklistItemStatus,
    ComplianceStatus,
    ManufacturingMetricsSummary,
)
from crewai_enterprise_pipeline_api.services.case_service import CaseService
from crewai_enterprise_pipeline_api.services.commercial_service import CommercialService
from crewai_enterprise_pipeline_api.services.financial_qoe_service import FinancialQoEService
from crewai_enterprise_pipeline_api.services.forensic_service import ForensicService
from crewai_enterprise_pipeline_api.services.operations_service import OperationsService
from crewai_enterprise_pipeline_api.services.regulatory_service import RegulatoryService
from crewai_enterprise_pipeline_api.services.sector_signal_utils import (
    collect_sector_text,
    extract_amount,
    extract_days,
    extract_percentage,
)

COMPLETED_CHECKLIST_STATUSES = {
    ChecklistItemStatus.SATISFIED.value,
    ChecklistItemStatus.NOT_APPLICABLE.value,
}

ASSET_REGISTER_PATTERN = re.compile(
    r"(?P<asset>[A-Za-z0-9 /&()-]{3,80}?)\s+wdv\s+(?P<wdv>\d[\d,]*(?:\.\d+)?)"
    r"(?:\s*(?P<wdv_unit>crore|cr|lakh|lac|million|mn|billion|bn)?)"
    r".{0,25}?replacement cost\s+(?P<replacement>\d[\d,]*(?:\.\d+)?)"
    r"(?:\s*(?P<replacement_unit>crore|cr|lakh|lac|million|mn|billion|bn)?)",
    re.IGNORECASE,
)


class ManufacturingService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.case_service = CaseService(session)
        self.commercial_service = CommercialService(session)
        self.financial_service = FinancialQoEService(session)
        self.forensic_service = ForensicService(session)
        self.operations_service = OperationsService(session)
        self.regulatory_service = RegulatoryService(session)

    async def build_manufacturing_metrics(
        self,
        case_id: str,
        *,
        persist_checklist: bool = True,
    ) -> ManufacturingMetricsSummary | None:
        case = await self.case_service._get_case_record(case_id)
        if case is None:
            return None

        financial_summary = await self.financial_service.build_financial_summary(
            case_id,
            persist_checklist=False,
        )
        commercial_summary = await self.commercial_service.build_commercial_summary(
            case_id,
            persist_checklist=False,
        )
        operations_summary = await self.operations_service.build_operations_summary(
            case_id,
            persist_checklist=False,
        )
        forensic_summary = await self.forensic_service.build_forensic_summary(
            case_id,
            persist_checklist=False,
        )
        compliance_summary = await self.regulatory_service.build_compliance_matrix(
            case_id,
            persist_checklist=False,
        )

        text = collect_sector_text(
            case,
            keywords=(
                "capacity utilization",
                "capacity utilisation",
                "dio",
                "dso",
                "dpo",
                "asset turnover",
                "replacement cost",
                "wdv",
                "maintenance backlog",
                "pollution control",
                "order book",
            ),
            workstream_domains=(
                "financial_qoe",
                "commercial",
                "operations",
                "regulatory",
                "forensic_compliance",
            ),
            document_kind_keywords=("plant", "inventory", "operations", "ehs", "factory", "capex"),
        )

        capacity_utilization = extract_percentage(
            text,
            "capacity utilization",
            "capacity utilisation",
            "utilization",
            "utilisation",
        )
        dio = extract_days(text, "dio", "days inventory outstanding", "inventory days")
        dso = extract_days(text, "dso", "days sales outstanding", "receivable days")
        dpo = extract_days(text, "dpo", "days payable outstanding", "payable days")
        asset_turnover = extract_amount(text, "asset turnover")
        if asset_turnover is None and financial_summary is not None:
            asset_turnover = financial_summary.ratios.get("asset_turnover")

        asset_register = self._extract_asset_register(text)
        flags = self._build_flags(
            commercial_summary,
            operations_summary,
            forensic_summary,
            compliance_summary,
            text=text,
            capacity_utilization=capacity_utilization,
            dio=dio,
            dso=dso,
            dpo=dpo,
            asset_register=asset_register,
        )

        summary = ManufacturingMetricsSummary(
            case_id=case_id,
            capacity_utilization=capacity_utilization,
            dio=dio,
            dso=dso,
            dpo=dpo,
            asset_turnover=asset_turnover,
            asset_register=asset_register,
            flags=flags,
        )
        if persist_checklist:
            summary.checklist_updates = await self._auto_update_checklist(
                case,
                summary,
                commercial_summary=commercial_summary,
                operations_summary=operations_summary,
                forensic_summary=forensic_summary,
                compliance_summary=compliance_summary,
            )
        return summary

    def _extract_asset_register(self, text: str) -> list[AssetRegisterItem]:
        items: list[AssetRegisterItem] = []
        seen_assets: set[tuple[str, float, float]] = set()
        for match in ASSET_REGISTER_PATTERN.finditer(text):
            carrying = extract_amount(
                match.group(0),
                "wdv",
            )
            replacement = extract_amount(
                match.group(0),
                "replacement cost",
            )
            if carrying is None or replacement is None:
                continue
            asset_name = " ".join(match.group("asset").split())
            fingerprint = (asset_name.lower(), carrying, replacement)
            if fingerprint in seen_assets:
                continue
            seen_assets.add(fingerprint)
            gap = replacement - carrying
            items.append(
                AssetRegisterItem(
                    asset_name=asset_name,
                    carrying_value=carrying,
                    replacement_cost=replacement,
                    replacement_gap=round(gap, 4),
                    note="Replacement cost exceeds WDV." if gap > 0 else "WDV exceeds replacement.",
                )
            )
        return items[:6]

    def _build_flags(
        self,
        commercial_summary,
        operations_summary,
        forensic_summary,
        compliance_summary,
        *,
        text: str,
        capacity_utilization: float | None,
        dio: float | None,
        dso: float | None,
        dpo: float | None,
        asset_register: list[AssetRegisterItem],
    ) -> list[str]:
        flags: list[str] = []
        if capacity_utilization is not None and capacity_utilization < 0.75:
            flags.append(
                "Capacity utilization is below 75%, indicating throughput under-absorption."
            )
        if dio is not None and dio > 90:
            flags.append("Inventory days exceed 90, indicating aging or slow-moving stock risk.")
        if dso is not None and dso > 75:
            flags.append("Receivable days exceed 75, indicating collection stress.")
        if dpo is not None and dpo < 30:
            flags.append("Payables cover is thin, which can tighten supplier funding headroom.")
        if any(
            item.replacement_gap is not None and item.replacement_gap > 0 for item in asset_register
        ):
            flags.append("Asset register shows replacement-cost gaps against carried plant values.")
        if operations_summary is not None and operations_summary.single_site_dependency:
            flags.append("Single-site dependence remains a material manufacturing continuity risk.")
        if operations_summary is not None and operations_summary.supplier_concentration_top_3:
            if operations_summary.supplier_concentration_top_3 >= 0.5:
                flags.append(
                    "Top suppliers account for at least 50% of spend, "
                    "creating input-concentration risk."
                )
        if compliance_summary is not None:
            regulatory_blockers = [
                item
                for item in compliance_summary.items
                if item.status in {
                    ComplianceStatus.NON_COMPLIANT,
                    ComplianceStatus.PARTIALLY_COMPLIANT,
                }
            ]
            if regulatory_blockers:
                flags.append(
                    "Manufacturing compliance matrix still has "
                    f"{len(regulatory_blockers)} EHS/factory gaps."
                )
        lowered_text = text.lower()
        if (
            commercial_summary is not None
            and commercial_summary.concentration_signals
            or (
                "order book" in lowered_text
                and any(token in lowered_text for token in ("dealer", "discount", "oem", "channel"))
            )
        ):
            flags.append("Order-book or channel concentration requires commercial review.")
        if forensic_summary is not None and forensic_summary.flags:
            flags.append("Procurement or capex integrity flags require forensic follow-up.")
        return flags[:7]

    async def _auto_update_checklist(
        self,
        case,
        summary: ManufacturingMetricsSummary,
        *,
        commercial_summary,
        operations_summary,
        forensic_summary,
        compliance_summary,
    ) -> list[ChecklistAutoUpdate]:
        condition_map = {
            "financial_qoe.inventory_quality": summary.dio is not None,
            "operations.plant_capacity_utilisation": summary.capacity_utilization is not None,
            "operations.supplier_concentration": bool(
                operations_summary
                and (
                    operations_summary.supplier_concentration_top_3 is not None
                    or operations_summary.dependency_signals
                )
            ),
            "regulatory.ehs_factory_compliance": bool(
                compliance_summary and compliance_summary.items
            ),
            "commercial.orderbook_channel_mix": bool(
                commercial_summary
                and (
                    commercial_summary.concentration_signals
                    or commercial_summary.pricing_signals
                    or commercial_summary.renewal_signals
                )
            ),
            "forensic.procurement_related_party": bool(
                forensic_summary and forensic_summary.flags
            ),
        }

        updated: list[ChecklistAutoUpdate] = []
        for item in case.checklist_items:
            template_key = item.template_key or ""
            if not condition_map.get(template_key):
                continue
            if item.status in COMPLETED_CHECKLIST_STATUSES:
                continue
            note = self._build_checklist_note(template_key, summary)
            item.status = ChecklistItemStatus.SATISFIED.value
            item.note = note
            updated.append(
                ChecklistAutoUpdate(
                    checklist_id=item.id,
                    template_key=template_key,
                    status=ChecklistItemStatus.SATISFIED,
                    note=note,
                )
            )
        if updated:
            await self.session.commit()
        return updated

    def _build_checklist_note(
        self,
        template_key: str,
        summary: ManufacturingMetricsSummary,
    ) -> str:
        if template_key == "financial_qoe.inventory_quality":
            return (
                "Auto-satisfied by Phase 12 Manufacturing engine with "
                f"DIO {summary.dio:.2f} days."
            )
        if template_key == "operations.plant_capacity_utilisation":
            return (
                "Auto-satisfied by Phase 12 Manufacturing engine with "
                f"capacity utilization {summary.capacity_utilization:.0%}."
            )
        if template_key == "operations.supplier_concentration":
            return (
                "Auto-satisfied by Phase 12 Manufacturing engine with "
                "supplier dependency review."
            )
        if template_key == "regulatory.ehs_factory_compliance":
            return (
                "Auto-satisfied by Phase 12 Manufacturing engine with "
                "EHS/factory compliance review."
            )
        if template_key == "commercial.orderbook_channel_mix":
            return "Auto-satisfied by Phase 12 Manufacturing engine with order-book/channel review."
        if template_key == "forensic.procurement_related_party":
            return (
                "Auto-satisfied by Phase 12 Manufacturing engine with "
                "procurement integrity review."
            )
        return "Auto-satisfied by Phase 12 Manufacturing engine."
