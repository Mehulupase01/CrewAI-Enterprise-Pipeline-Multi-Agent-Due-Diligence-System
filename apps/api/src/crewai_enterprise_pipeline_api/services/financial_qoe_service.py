from __future__ import annotations

from collections import defaultdict
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from crewai_enterprise_pipeline_api.domain.models import (
    ChecklistAutoUpdate,
    ChecklistItemStatus,
    FinancialMetricSummary,
    FinancialPeriod,
    FinancialStatement,
    SectorPack,
)
from crewai_enterprise_pipeline_api.ingestion.financial_parser import FinancialParser
from crewai_enterprise_pipeline_api.services.case_service import CaseService
from crewai_enterprise_pipeline_api.storage.service import DocumentStorageService

COMPLETED_CHECKLIST_STATUSES = {
    ChecklistItemStatus.SATISFIED.value,
    ChecklistItemStatus.NOT_APPLICABLE.value,
}

FINANCIAL_DOCUMENT_KEYWORDS = (
    "financial",
    "audit",
    "qoe",
    "bridge",
    "monthly",
    "borrower",
    "underwriting",
    "portfolio",
    "inventory",
    "cash flow",
    "debt",
    "p&l",
    "profit",
)


class FinancialQoEService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.case_service = CaseService(session)
        self.storage = DocumentStorageService()
        self.parser = FinancialParser()

    async def build_financial_summary(
        self,
        case_id: str,
        *,
        persist_checklist: bool = True,
    ) -> FinancialMetricSummary | None:
        case = await self.case_service._get_case_record(case_id)
        if case is None:
            return None

        statements: list[FinancialStatement] = []
        for artifact in self._candidate_artifacts(case):
            if not artifact.storage_path:
                continue
            content = self.storage.retrieve_bytes(artifact.storage_path)
            if content is None:
                continue
            fallback_text = "\n\n".join(chunk.text for chunk in getattr(artifact, "chunks", []))
            statement = self.parser.parse_document(
                artifact_id=artifact.id,
                artifact_title=artifact.title,
                document_kind=artifact.document_kind,
                filename=artifact.original_filename or artifact.title,
                mime_type=artifact.mime_type,
                parser_name=artifact.parser_name,
                content=content,
                fallback_text=fallback_text,
            )
            if statement is not None and (statement.periods or statement.qoe_adjustments):
                statements.append(statement)

        periods = self._merge_periods(statements)
        adjustments = self._merge_adjustments(statements)
        normalized_ebitda = self._compute_normalized_ebitda(periods, adjustments)
        ratios = self._compute_ratios(periods)
        flags = self._detect_flags(periods, ratios)
        checklist_updates: list[ChecklistAutoUpdate] = []

        summary = FinancialMetricSummary(
            case_id=case_id,
            statement_count=len(statements),
            statements=statements,
            periods=periods,
            ratios=ratios,
            qoe_adjustments=adjustments,
            normalized_ebitda=normalized_ebitda,
            flags=flags,
        )

        if persist_checklist:
            checklist_updates = await self._auto_update_checklist(case, summary)
            summary.checklist_updates = checklist_updates

        return summary

    def _candidate_artifacts(self, case) -> list:
        financial_artifact_ids = {
            item.artifact_id
            for item in case.evidence_items
            if item.workstream_domain == "financial_qoe" and getattr(item, "artifact_id", None)
        }
        candidates: list = []
        for artifact in case.documents:
            title_source = " ".join(
                filter(
                    None,
                    [
                        artifact.title,
                        artifact.document_kind,
                        artifact.original_filename,
                    ],
                )
            ).lower()
            if artifact.id in financial_artifact_ids or any(
                keyword in title_source for keyword in FINANCIAL_DOCUMENT_KEYWORDS
            ):
                candidates.append(artifact)
        return candidates

    def _merge_periods(self, statements: list[FinancialStatement]) -> list[FinancialPeriod]:
        merged: dict[str, dict[str, float | None]] = defaultdict(dict)
        for statement in statements:
            for period in statement.periods:
                payload = period.model_dump(exclude={"label"})
                target = merged[period.label]
                for field_name, value in payload.items():
                    if value is None:
                        continue
                    if field_name in {"customer_concentration_top_3", "q4_revenue_share"}:
                        existing = target.get(field_name)
                        if existing is None or value > existing:
                            target[field_name] = value
                        continue
                    target[field_name] = value

        def _sort_key(item: tuple[str, dict[str, float | None]]) -> tuple[int, int]:
            label = item[0]
            if label.startswith("Q"):
                quarter = int(label[1])
                year = int(label[-2:]) + 2000
                return (year, quarter)
            return (int(label[-2:]) + 2000, 5)

        return [
            FinancialPeriod(label=label, **values)
            for label, values in sorted(merged.items(), key=_sort_key)
        ]

    def _merge_adjustments(self, statements: list[FinancialStatement]):
        unique: dict[tuple[str, str], Any] = {}
        for statement in statements:
            for adjustment in statement.qoe_adjustments:
                unique[(adjustment.label.lower(), adjustment.category.lower())] = adjustment
        return sorted(unique.values(), key=lambda item: (item.category, item.label))

    def _compute_normalized_ebitda(self, periods, adjustments) -> float | None:
        if not periods or periods[-1].ebitda is None:
            return None
        return round(periods[-1].ebitda - sum(item.amount for item in adjustments), 4)

    def _compute_ratios(self, periods: list[FinancialPeriod]) -> dict[str, float | None]:
        if not periods:
            return {}

        latest = periods[-1]
        ratios: dict[str, float | None] = {
            "revenue_cagr_3y": self._revenue_cagr(periods, years=3),
            "revenue_growth_latest_yoy": self._latest_revenue_growth(periods),
            "ebitda_margin": self._ratio(latest.ebitda, latest.revenue),
            "gross_margin": self._ratio(latest.gross_profit, latest.revenue),
            "operating_margin": self._ratio(latest.operating_profit, latest.revenue),
            "pat_margin": self._ratio(latest.pat, latest.revenue),
            "cash_conversion": self._ratio(latest.operating_cash_flow, latest.ebitda),
            "debt_to_ebitda": self._ratio(latest.net_debt, latest.ebitda),
            "interest_coverage": self._interest_coverage(latest.ebitda, latest.interest_expense),
            "working_capital_days": self._working_capital_days(
                latest.working_capital, latest.revenue
            ),
            "asset_turnover": self._ratio(latest.revenue, latest.total_assets),
            "return_on_assets": self._ratio(latest.pat, latest.total_assets),
            "return_on_equity": self._ratio(latest.pat, latest.shareholder_equity),
            "debt_to_equity": self._ratio(latest.net_debt, latest.shareholder_equity),
        }
        return {key: self._round_if_number(value) for key, value in ratios.items()}

    def _detect_flags(
        self,
        periods: list[FinancialPeriod],
        ratios: dict[str, float | None],
    ) -> list[str]:
        flags: list[str] = []
        if not periods:
            return flags

        latest = periods[-1]
        if latest.customer_concentration_top_3 and latest.customer_concentration_top_3 > 0.60:
            flags.append(
                "Revenue concentration: top 3 customers exceed 60% of the latest period."
            )
        if (
            latest.operating_cash_flow is not None
            and latest.operating_cash_flow < 0
            and latest.ebitda is not None
            and latest.ebitda > 0
        ):
            flags.append(
                "Cash conversion concern: operating cash flow is negative despite positive EBITDA."
            )
        if self._growth_trend_declining(periods):
            flags.append(
                "Revenue growth trend is declining across the most recent year-on-year periods."
            )
        if latest.q4_revenue_share and latest.q4_revenue_share > 0.40:
            flags.append(
                "Revenue seasonality concern: Q4 contributes more than 40% of annual revenue."
            )
        if ratios.get("debt_to_ebitda") is not None and ratios["debt_to_ebitda"] > 4.0:
            flags.append("Leverage concern: net debt exceeds 4.0x EBITDA.")
        if ratios.get("interest_coverage") is not None and ratios["interest_coverage"] < 2.0:
            flags.append("Coverage concern: interest coverage is below 2.0x.")
        return sorted(set(flags))

    async def _auto_update_checklist(
        self,
        case,
        summary: FinancialMetricSummary,
    ) -> list[ChecklistAutoUpdate]:
        condition_map = self._condition_map(case, summary)
        if not condition_map:
            return []

        updated: list[ChecklistAutoUpdate] = []
        for item in case.checklist_items:
            template_key = item.template_key or ""
            if template_key not in condition_map:
                continue
            if not condition_map[template_key]:
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

    def _condition_map(self, case, summary: FinancialMetricSummary) -> dict[str, bool]:
        latest = summary.periods[-1] if summary.periods else None
        document_tokens = " ".join(
            filter(
                None,
                [
                    document.document_kind.lower()
                    for document in case.documents
                    if any(
                        keyword in document.document_kind.lower()
                        for keyword in FINANCIAL_DOCUMENT_KEYWORDS
                    )
                ],
            )
        )
        has_multi_period_financials = len(summary.periods) >= 3 and latest is not None
        has_bridge_signal = "monthly" in document_tokens or "bridge" in document_tokens
        has_debt_metrics = any(
            summary.ratios.get(key) is not None
            for key in ("debt_to_ebitda", "interest_coverage")
        )
        has_working_capital = summary.ratios.get("working_capital_days") is not None
        has_inventory_signal = "inventory" in document_tokens and has_working_capital
        has_bfsi_asset_signal = (
            case.sector_pack == SectorPack.BFSI_NBFC.value
            and has_multi_period_financials
            and any(token in document_tokens for token in ("portfolio", "provision", "asset"))
        )
        has_alm_signal = (
            case.sector_pack == SectorPack.BFSI_NBFC.value
            and any(token in document_tokens for token in ("alm", "liquidity", "treasury"))
        )

        return {
            "financial_qoe.audited_financials": has_multi_period_financials,
            "financial_qoe.monthly_bridge": has_bridge_signal,
            "financial_qoe.borrower_statements": has_multi_period_financials,
            "financial_qoe.debt_service_capacity": has_debt_metrics,
            "financial_qoe.working_capital_behaviour": has_working_capital,
            "financial_qoe.inventory_quality": has_inventory_signal,
            "financial_qoe.asset_quality_and_provisioning": has_bfsi_asset_signal,
            "financial_qoe.alm_liquidity_profile": has_alm_signal,
        }

    def _build_checklist_note(
        self,
        template_key: str,
        summary: FinancialMetricSummary,
    ) -> str:
        latest = summary.periods[-1] if summary.periods else None
        period_labels = (
            ", ".join(period.label for period in summary.periods[:5]) or "no periods"
        )
        fragments = [
            "Auto-satisfied by Phase 8 Financial QoE engine from periods: "
            f"{period_labels}."
        ]
        if latest and latest.revenue is not None:
            fragments.append(f"Latest revenue: {latest.revenue:.2f}.")
        if latest and latest.ebitda is not None:
            fragments.append(f"Latest EBITDA: {latest.ebitda:.2f}.")
        if summary.normalized_ebitda is not None:
            fragments.append(f"Normalized EBITDA: {summary.normalized_ebitda:.2f}.")
        if template_key.endswith("debt_service_capacity"):
            coverage = summary.ratios.get("interest_coverage")
            leverage = summary.ratios.get("debt_to_ebitda")
            if coverage is not None:
                fragments.append(f"Interest coverage: {coverage:.2f}x.")
            if leverage is not None:
                fragments.append(f"Debt/EBITDA: {leverage:.2f}x.")
        if template_key.endswith("working_capital_behaviour"):
            wc_days = summary.ratios.get("working_capital_days")
            if wc_days is not None:
                fragments.append(f"Working-capital days: {wc_days:.2f}.")
        return " ".join(fragments)

    def _revenue_cagr(self, periods: list[FinancialPeriod], *, years: int) -> float | None:
        annual_periods = [period for period in periods if period.label.startswith("FY")]
        if len(annual_periods) < years + 1:
            return None
        earliest = annual_periods[-(years + 1)]
        latest = annual_periods[-1]
        if not earliest.revenue or not latest.revenue or earliest.revenue <= 0:
            return None
        return (latest.revenue / earliest.revenue) ** (1 / years) - 1

    def _latest_revenue_growth(self, periods: list[FinancialPeriod]) -> float | None:
        annual_periods = [period for period in periods if period.label.startswith("FY")]
        if len(annual_periods) < 2:
            return None
        previous = annual_periods[-2]
        latest = annual_periods[-1]
        if not previous.revenue or not latest.revenue or previous.revenue == 0:
            return None
        return (latest.revenue / previous.revenue) - 1

    def _growth_trend_declining(self, periods: list[FinancialPeriod]) -> bool:
        annual_periods = [period for period in periods if period.label.startswith("FY")]
        growth_rates: list[float] = []
        for previous, current in zip(annual_periods, annual_periods[1:], strict=False):
            if not previous.revenue or not current.revenue or previous.revenue == 0:
                continue
            growth_rates.append((current.revenue / previous.revenue) - 1)
        if len(growth_rates) < 2:
            return False
        return all(
            current < previous
            for previous, current in zip(growth_rates, growth_rates[1:], strict=False)
        )

    def _ratio(self, numerator: float | None, denominator: float | None) -> float | None:
        if numerator is None or denominator in {None, 0}:
            return None
        return numerator / denominator

    def _interest_coverage(
        self,
        ebitda: float | None,
        interest_expense: float | None,
    ) -> float | None:
        if ebitda is None or interest_expense in {None, 0}:
            return None
        return ebitda / abs(interest_expense)

    def _working_capital_days(
        self,
        working_capital: float | None,
        revenue: float | None,
    ) -> float | None:
        if working_capital is None or revenue in {None, 0}:
            return None
        return (working_capital / revenue) * 365

    def _round_if_number(self, value: float | None) -> float | None:
        if value is None:
            return None
        return round(value, 4)
