from __future__ import annotations

import re

from sqlalchemy.ext.asyncio import AsyncSession

from crewai_enterprise_pipeline_api.domain.models import (
    BorrowerScorecard,
    BorrowerScoreSection,
    ChecklistAutoUpdate,
    ChecklistItemStatus,
    CovenantTrackingItem,
    FlagSeverity,
)
from crewai_enterprise_pipeline_api.services.case_service import CaseService
from crewai_enterprise_pipeline_api.services.document_signal_utils import (
    collect_artifact_snapshots,
    score_snapshot_relevance,
)
from crewai_enterprise_pipeline_api.services.financial_qoe_service import FinancialQoEService
from crewai_enterprise_pipeline_api.services.legal_service import LegalService

COMPLETED_CHECKLIST_STATUSES = {
    ChecklistItemStatus.SATISFIED.value,
    ChecklistItemStatus.NOT_APPLICABLE.value,
}

COVENANT_PATTERN = re.compile(
    r"(dscr|interest coverage|debt[ /-]?to[ /-]?ebitda|covenant|waiver|default|days past due|dpd)",
    re.IGNORECASE,
)


class CreditService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.case_service = CaseService(session)
        self.financial_service = FinancialQoEService(session)
        self.legal_service = LegalService(session)

    async def build_borrower_scorecard(
        self,
        case_id: str,
        *,
        persist_checklist: bool = True,
    ) -> BorrowerScorecard | None:
        case = await self.case_service._get_case_record(case_id)
        if case is None:
            return None

        financial_summary = await self.financial_service.build_financial_summary(
            case_id,
            persist_checklist=False,
        )
        legal_summary = await self.legal_service.build_legal_summary(
            case_id,
            persist_checklist=False,
        )
        covenant_tracking = self._build_covenant_tracking(case)

        financial_section = self._score_financial_health(case, financial_summary)
        collateral_section = self._score_collateral(case, legal_summary)
        covenant_section = self._score_covenants(case, financial_summary, covenant_tracking)
        overall_score = round(
            (financial_section.score * 0.5)
            + (collateral_section.score * 0.25)
            + (covenant_section.score * 0.25)
        )
        overall_rating = self._score_band(overall_score)

        summary = BorrowerScorecard(
            case_id=case_id,
            financial_health=financial_section,
            collateral=collateral_section,
            covenants=covenant_section,
            overall_score=overall_score,
            overall_rating=overall_rating,
            covenant_tracking=covenant_tracking,
        )
        if persist_checklist:
            summary.checklist_updates = await self._auto_update_checklist(case, summary)
        return summary

    def _score_financial_health(self, case, financial_summary) -> BorrowerScoreSection:
        score = 70
        reasons: list[str] = []
        flags: list[str] = []
        evidence_ids: list[str] = []

        if financial_summary is None or not financial_summary.periods:
            score = 35
            reasons.append("No structured financial package is available for underwriting.")
        else:
            evidence_ids = [
                statement.artifact_id
                for statement in financial_summary.statements
                if statement.artifact_id
            ][:3]
            interest_coverage = financial_summary.ratios.get("interest_coverage")
            debt_to_ebitda = financial_summary.ratios.get("debt_to_ebitda")
            cash_conversion = financial_summary.ratios.get("cash_conversion")
            if interest_coverage is not None:
                reasons.append(f"Interest coverage is {interest_coverage:.2f}x.")
                if interest_coverage >= 4:
                    score += 8
                elif interest_coverage >= 2:
                    score += 2
                else:
                    score -= 16
                    flags.append("Coverage is below comfortable underwriting tolerance.")
            if debt_to_ebitda is not None:
                reasons.append(f"Debt to EBITDA is {debt_to_ebitda:.2f}x.")
                if debt_to_ebitda <= 2:
                    score += 8
                elif debt_to_ebitda <= 4:
                    score += 2
                else:
                    score -= 16
                    flags.append("Leverage is elevated relative to earnings.")
            if cash_conversion is not None:
                reasons.append(f"Cash conversion is {cash_conversion:.2f}x.")
                if cash_conversion >= 0.8:
                    score += 5
                elif cash_conversion < 0.4:
                    score -= 10
                    flags.append("Cash conversion is weak versus reported earnings.")
            if financial_summary.flags:
                flags.extend(financial_summary.flags[:3])
                score -= min(len(financial_summary.flags) * 4, 12)

        blocking_issues = [
            issue
            for issue in case.issues
            if issue.workstream_domain == "financial_qoe"
            and issue.severity in {FlagSeverity.HIGH.value, FlagSeverity.CRITICAL.value}
        ]
        if blocking_issues:
            score -= min(len(blocking_issues) * 6, 18)
            reasons.append(
                f"{len(blocking_issues)} high-severity financial issues remain unresolved."
            )

        score = self._clamp_score(score)
        return BorrowerScoreSection(
            score=score,
            rating=self._score_band(score),
            rationale=" ".join(reasons) or "Financial health has not yet been assessed.",
            flags=flags[:5],
            evidence_ids=evidence_ids,
        )

    def _score_collateral(self, case, legal_summary) -> BorrowerScoreSection:
        score = 60
        reasons: list[str] = []
        flags: list[str] = []
        evidence_ids: list[str] = []

        snapshots = [
            snapshot
            for snapshot in collect_artifact_snapshots(case)
            if score_snapshot_relevance(
                snapshot,
                workstream_domains=("legal_corporate", "financial_qoe"),
                keywords=("collateral", "charge", "security", "hypothecation", "pledge"),
                document_kind_keywords=("security", "charge", "collateral"),
            )
            > 0
        ]
        if snapshots:
            score += 10
            evidence_ids = [
                evidence_id for snapshot in snapshots for evidence_id in snapshot.evidence_ids[:1]
            ][:3]
            reasons.append(
                f"Collateral or security evidence exists across {len(snapshots)} document sets."
            )
        else:
            score -= 10
            flags.append("Collateral evidence is thin for the current case.")

        if legal_summary is not None and legal_summary.charges_detected:
            score += 6
            reasons.append(
                f"{legal_summary.charges_detected} charge or encumbrance references were detected."
            )
        legal_blockers = [
            issue
            for issue in case.issues
            if issue.workstream_domain == "legal_corporate"
            and issue.severity in {FlagSeverity.HIGH.value, FlagSeverity.CRITICAL.value}
            and any(
                token in issue.title.lower()
                for token in ("charge", "encumbrance", "collateral", "security")
            )
        ]
        if legal_blockers:
            score -= min(len(legal_blockers) * 8, 20)
            flags.append("Collateral perfection or encumbrance blockers remain open.")
        score = self._clamp_score(score)
        return BorrowerScoreSection(
            score=score,
            rating=self._score_band(score),
            rationale=" ".join(reasons) or "Collateral quality has not yet been assessed.",
            flags=flags[:5],
            evidence_ids=evidence_ids,
        )

    def _score_covenants(self, case, financial_summary, covenant_tracking) -> BorrowerScoreSection:
        score = 65
        reasons: list[str] = []
        flags: list[str] = []
        evidence_ids: list[str] = [
            evidence_id for item in covenant_tracking for evidence_id in item.evidence_ids[:1]
        ][:3]

        if covenant_tracking:
            reasons.append(f"{len(covenant_tracking)} covenant or warning signals were extracted.")
            breached = [
                item
                for item in covenant_tracking
                if item.status in {"breached", "waiver_required"}
            ]
            if breached:
                score -= min(len(breached) * 12, 24)
                flags.append("At least one covenant item is breached or waiver-dependent.")
            else:
                score += 5
        else:
            score -= 10
            reasons.append("No structured covenant evidence was found.")

        if financial_summary is not None:
            leverage = financial_summary.ratios.get("debt_to_ebitda")
            coverage = financial_summary.ratios.get("interest_coverage")
            if leverage is not None and leverage > 4:
                score -= 10
                flags.append("Leverage pressure reduces covenant headroom.")
            if coverage is not None and coverage < 2:
                score -= 10
                flags.append("Low interest coverage reduces covenant resilience.")

        covenant_issues = [
            issue
            for issue in case.issues
            if issue.workstream_domain in {"financial_qoe", "regulatory"}
            and issue.severity in {FlagSeverity.HIGH.value, FlagSeverity.CRITICAL.value}
            and any(
                token in issue.title.lower() for token in ("covenant", "default", "debt service")
            )
        ]
        if covenant_issues:
            score -= min(len(covenant_issues) * 8, 16)
            reasons.append(
                f"{len(covenant_issues)} covenant-related issue-register blockers are open."
            )
        score = self._clamp_score(score)
        return BorrowerScoreSection(
            score=score,
            rating=self._score_band(score),
            rationale=" ".join(reasons) or "Covenant position has not yet been assessed.",
            flags=flags[:5],
            evidence_ids=evidence_ids,
        )

    def _build_covenant_tracking(self, case) -> list[CovenantTrackingItem]:
        items: list[CovenantTrackingItem] = []

        for evidence in case.evidence_items:
            haystack = " ".join(filter(None, [evidence.title, evidence.excerpt]))
            if not COVENANT_PATTERN.search(haystack):
                continue
            lowered = haystack.lower()
            status = "monitor"
            if any(
                token in lowered
                for token in ("breach", "default", "days past due", "dpd", "past due")
            ):
                status = "breached"
            elif "waiver" in lowered:
                status = "waiver_required"
            elif any(token in lowered for token in ("headroom", "compliant", "within threshold")):
                status = "compliant"
            items.append(
                CovenantTrackingItem(
                    name=evidence.title,
                    status=status,
                    note=evidence.excerpt,
                    evidence_ids=[evidence.id],
                )
            )

        for issue in case.issues:
            lowered = " ".join(filter(None, [issue.title, issue.summary])).lower()
            if not COVENANT_PATTERN.search(lowered):
                continue
            items.append(
                CovenantTrackingItem(
                    name=issue.title,
                    status=(
                        "breached"
                        if issue.severity
                        in {FlagSeverity.HIGH.value, FlagSeverity.CRITICAL.value}
                        else "monitor"
                    ),
                    note=issue.business_impact,
                    evidence_ids=[issue.source_evidence_id] if issue.source_evidence_id else [],
                )
            )

        deduped: list[CovenantTrackingItem] = []
        seen: set[str] = set()
        for item in items:
            key = item.name.lower()
            if key in seen:
                continue
            seen.add(key)
            deduped.append(item)
        return deduped[:8]

    async def _auto_update_checklist(
        self,
        case,
        summary: BorrowerScorecard,
    ) -> list[ChecklistAutoUpdate]:
        condition_map = {
            "financial_qoe.borrower_scorecard": summary.financial_health.score > 0,
            "legal_corporate.collateral_cover_matrix": summary.collateral.score > 0,
            "regulatory.covenant_tracking_pack": bool(summary.covenant_tracking),
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

    def _build_checklist_note(self, template_key: str, summary: BorrowerScorecard) -> str:
        if template_key == "financial_qoe.borrower_scorecard":
            return (
                "Auto-satisfied by Phase 11 Credit engine with borrower score "
                f"{summary.overall_score}/100."
            )
        if template_key == "legal_corporate.collateral_cover_matrix":
            return (
                "Auto-satisfied by Phase 11 Credit engine with collateral score "
                f"{summary.collateral.score}/100."
            )
        if template_key == "regulatory.covenant_tracking_pack":
            return (
                "Auto-satisfied by Phase 11 Credit engine with "
                f"{len(summary.covenant_tracking)} covenant tracking items."
            )
        return "Auto-satisfied by Phase 11 Credit engine."

    def _score_band(self, score: int) -> str:
        if score >= 80:
            return "strong"
        if score >= 65:
            return "adequate"
        if score >= 50:
            return "watchlist"
        return "stressed"

    def _clamp_score(self, score: int) -> int:
        return max(0, min(100, int(round(score))))
