from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from crewai_enterprise_pipeline_api.db.models import EvidenceNodeRecord, IssueRegisterItemRecord
from crewai_enterprise_pipeline_api.domain.models import (
    FlagSeverity,
    IssueRegisterItemSummary,
    IssueScanResult,
    IssueStatus,
    MotionPack,
    WorkstreamDomain,
)
from crewai_enterprise_pipeline_api.services.case_service import CaseService


@dataclass(frozen=True)
class HeuristicIssueRule:
    title: str
    severity: FlagSeverity
    business_impact: str
    recommended_action: str
    patterns: tuple[str, ...]
    workstream_override: WorkstreamDomain | None = None
    motion_packs: tuple[MotionPack, ...] | None = None


HEURISTIC_RULES: tuple[HeuristicIssueRule, ...] = (
    HeuristicIssueRule(
        title="Outstanding tax or GST exposure",
        severity=FlagSeverity.HIGH,
        business_impact=(
            "Potential cash leakage, penalties, and a higher likelihood of tax escrow or "
            "closing adjustments."
        ),
        recommended_action=(
            "Obtain the notice set, response filings, payment history, and management's "
            "remediation plan before sign-off."
        ),
        patterns=("gst notice", "gst demand", "tax notice", "tax demand", "show cause"),
        workstream_override=WorkstreamDomain.TAX,
    ),
    HeuristicIssueRule(
        title="Encumbrance or security interest risk",
        severity=FlagSeverity.HIGH,
        business_impact=(
            "Charges, pledges, or liens may constrain closing deliverables and reduce "
            "financing flexibility."
        ),
        recommended_action=(
            "Validate the latest charge register, release status, and lender consents "
            "needed before completion."
        ),
        patterns=("charge", "encumbrance", "lien", "pledge"),
        workstream_override=WorkstreamDomain.LEGAL_CORPORATE,
    ),
    HeuristicIssueRule(
        title="Litigation or dispute exposure",
        severity=FlagSeverity.HIGH,
        business_impact=(
            "Open claims or arbitration may create contingent liabilities, reputational "
            "harm, and closing conditions."
        ),
        recommended_action=(
            "Collect pleadings, counsel assessment, provisioning logic, and likely "
            "settlement range."
        ),
        patterns=("litigation", "arbitration", "claim", "dispute"),
        workstream_override=WorkstreamDomain.LEGAL_CORPORATE,
    ),
    HeuristicIssueRule(
        title="Related-party transaction scrutiny required",
        severity=FlagSeverity.HIGH,
        business_impact=(
            "Unclear promoter or related-party flows can distort normalized earnings and "
            "create governance or leakage concerns."
        ),
        recommended_action=(
            "Reconcile related-party ledgers, board approvals, transfer pricing support, "
            "and arm's-length rationale."
        ),
        patterns=("related party", "related-party", "promoter entity", "group company"),
        workstream_override=WorkstreamDomain.FORENSIC_COMPLIANCE,
    ),
    HeuristicIssueRule(
        title="Cybersecurity or privacy control weakness",
        severity=FlagSeverity.HIGH,
        business_impact=(
            "Security incidents or DPDP-related weaknesses can create regulatory, "
            "contractual, and remediation exposure."
        ),
        recommended_action=(
            "Review incident logs, security controls, data maps, processor contracts, and "
            "privacy remediation backlog."
        ),
        patterns=("data leak", "data breach", "privacy incident", "dpdp", "security incident"),
        workstream_override=WorkstreamDomain.CYBER_PRIVACY,
    ),
    HeuristicIssueRule(
        title="Customer concentration risk",
        severity=FlagSeverity.MEDIUM,
        business_impact=(
            "Revenue concentration can weaken forecast reliability and increase downside if "
            "a top account churns."
        ),
        recommended_action=(
            "Quantify top-customer exposure, renewal terms, churn sensitivity, and "
            "dependence by product and geography."
        ),
        patterns=("customer concentration", "top customer", "single customer"),
        workstream_override=WorkstreamDomain.COMMERCIAL,
    ),
    HeuristicIssueRule(
        title="Debt-service or covenant stress",
        severity=FlagSeverity.HIGH,
        business_impact=(
            "Weak debt-service coverage or covenant pressure can impair repayment capacity "
            "and trigger lender intervention."
        ),
        recommended_action=(
            "Recompute debt-service ratios, test covenant headroom, and obtain lender-side "
            "waiver or cure details."
        ),
        patterns=("covenant breach", "default", "dscr", "debt service", "days past due"),
        workstream_override=WorkstreamDomain.FINANCIAL_QOE,
        motion_packs=(MotionPack.CREDIT_LENDING,),
    ),
    HeuristicIssueRule(
        title="Fund diversion or end-use deviation risk",
        severity=FlagSeverity.HIGH,
        business_impact=(
            "Potential diversion of funds or end-use deviation can change the lending risk "
            "profile and create governance or enforcement exposure."
        ),
        recommended_action=(
            "Trace bank flows, related-party transactions, and end-use documentation before "
            "credit approval."
        ),
        patterns=("fund diversion", "end use deviation", "end-use deviation", "round tripping"),
        workstream_override=WorkstreamDomain.FORENSIC_COMPLIANCE,
        motion_packs=(MotionPack.CREDIT_LENDING,),
    ),
    HeuristicIssueRule(
        title="Collateral perfection gap",
        severity=FlagSeverity.HIGH,
        business_impact=(
            "Unperfected collateral or missing charge filings can weaken enforceability and "
            "reduce lender recovery."
        ),
        recommended_action=(
            "Validate the charge register, perfection filings, insurance coverage, and any "
            "third-party consent dependencies."
        ),
        patterns=("collateral gap", "security not perfected", "charge not filed", "unperfected"),
        workstream_override=WorkstreamDomain.LEGAL_CORPORATE,
        motion_packs=(MotionPack.CREDIT_LENDING,),
    ),
    HeuristicIssueRule(
        title="Borrowing-base or collateral shortfall",
        severity=FlagSeverity.HIGH,
        business_impact=(
            "A weak borrowing base or collateral shortfall can reduce sanctioned capacity, "
            "tighten covenants, or require additional support."
        ),
        recommended_action=(
            "Rebuild the borrowing base, validate eligibility haircuts, and confirm whether "
            "additional collateral or promoter support is needed."
        ),
        patterns=("borrowing base", "collateral shortfall", "security cover", "margin shortfall"),
        workstream_override=WorkstreamDomain.LEGAL_CORPORATE,
        motion_packs=(MotionPack.CREDIT_LENDING,),
    ),
    HeuristicIssueRule(
        title="Third-party integrity or bribery concern",
        severity=FlagSeverity.HIGH,
        business_impact=(
            "Integrity concerns can create bribery, fraud, reputational, and onboarding "
            "approval risk."
        ),
        recommended_action=(
            "Collect diligence responses, beneficial-owner details, and integrity "
            "supporting evidence before approval."
        ),
        patterns=("bribery", "kickback", "integrity concern", "conflict of interest"),
        workstream_override=WorkstreamDomain.FORENSIC_COMPLIANCE,
        motion_packs=(MotionPack.VENDOR_ONBOARDING,),
    ),
    HeuristicIssueRule(
        title="Sanctions or watchlist screening concern",
        severity=FlagSeverity.HIGH,
        business_impact=(
            "Sanctions or watchlist alerts can block onboarding and require legal or "
            "compliance escalation."
        ),
        recommended_action=(
            "Validate screening results, escalate false-positive review, and confirm "
            "onboarding restrictions before proceeding."
        ),
        patterns=("sanctions", "watchlist", "pep", "aml alert"),
        workstream_override=WorkstreamDomain.REGULATORY,
        motion_packs=(MotionPack.VENDOR_ONBOARDING,),
    ),
    HeuristicIssueRule(
        title="Vendor questionnaire or certification gap",
        severity=FlagSeverity.HIGH,
        business_impact=(
            "Incomplete questionnaires or missing certifications can block vendor approval "
            "and increase third-party oversight requirements."
        ),
        recommended_action=(
            "Collect the missing questionnaire responses, attestations, and certification evidence "
            "before approval."
        ),
        patterns=(
            "questionnaire incomplete",
            "missing certification",
            "soc 2",
            "iso certificate expired",
        ),
        workstream_override=WorkstreamDomain.CYBER_PRIVACY,
        motion_packs=(MotionPack.VENDOR_ONBOARDING,),
    ),
    HeuristicIssueRule(
        title="Critical vendor continuity dependency",
        severity=FlagSeverity.HIGH,
        business_impact=(
            "Single-vendor or single-location dependence can create service disruption and "
            "business continuity risk."
        ),
        recommended_action=(
            "Escalate continuity planning, confirm failover expectations, and document approval "
            "conditions for critical dependencies."
        ),
        patterns=("critical vendor", "single vendor", "single location", "single point of failure"),
        workstream_override=WorkstreamDomain.OPERATIONS,
        motion_packs=(MotionPack.VENDOR_ONBOARDING,),
    ),
    HeuristicIssueRule(
        title="Purchase-price adjustment or valuation sensitivity",
        severity=FlagSeverity.HIGH,
        business_impact=(
            "A valuation sensitivity can affect equity value, SPA economics, and the "
            "investment committee recommendation."
        ),
        recommended_action=(
            "Translate the issue into the valuation bridge and define the corresponding SPA "
            "protection or pricing adjustment."
        ),
        patterns=(
            "purchase price adjustment",
            "working capital peg",
            "valuation adjustment",
            "closing accounts",
        ),
        workstream_override=WorkstreamDomain.FINANCIAL_QOE,
        motion_packs=(MotionPack.BUY_SIDE_DILIGENCE,),
    ),
    HeuristicIssueRule(
        title="SPA protection or indemnity hotspot",
        severity=FlagSeverity.HIGH,
        business_impact=(
            "Unresolved indemnity, consent, or CP items can delay signing or closing and weaken "
            "deal protection."
        ),
        recommended_action=(
            "Escalate into the SPA issue matrix and map the item to indemnity, escrow, or "
            "condition-precedent treatment."
        ),
        patterns=("indemnity", "condition precedent", "consent required", "change of control"),
        workstream_override=WorkstreamDomain.LEGAL_CORPORATE,
        motion_packs=(MotionPack.BUY_SIDE_DILIGENCE,),
    ),
    HeuristicIssueRule(
        title="PMI readiness or integration dependency",
        severity=FlagSeverity.MEDIUM,
        business_impact=(
            "Unclear Day 1 ownership, system dependencies, or people transitions can delay "
            "integration benefits and create continuity risk."
        ),
        recommended_action=(
            "Move the issue into the PMI plan with Day 1 owners, TSA needs, and Day 100 actions."
        ),
        patterns=("day 1", "day 100", "integration risk", "tsa", "transition service"),
        workstream_override=WorkstreamDomain.OPERATIONS,
        motion_packs=(MotionPack.BUY_SIDE_DILIGENCE,),
    ),
    HeuristicIssueRule(
        title="Environmental or factory compliance exposure",
        severity=FlagSeverity.HIGH,
        business_impact=(
            "Environmental, safety, or factory compliance failures can create shutdown, "
            "remediation, and indemnity exposure."
        ),
        recommended_action=(
            "Collect licence status, notice history, remediation plan, and expected "
            "shutdown or capex implications."
        ),
        patterns=(
            "pollution control",
            "consent to operate",
            "factory licence",
            "ehs violation",
            "environmental notice",
        ),
        workstream_override=WorkstreamDomain.REGULATORY,
    ),
    HeuristicIssueRule(
        title="Inventory obsolescence or aging risk",
        severity=FlagSeverity.MEDIUM,
        business_impact=(
            "Aging or obsolete inventory can distort working capital, gross margin, and "
            "realisable asset value."
        ),
        recommended_action=(
            "Review aging buckets, NRV logic, scrap trends, and stock provisioning "
            "support by SKU and plant."
        ),
        patterns=("inventory aging", "obsolete stock", "slow moving inventory", "scrap write-off"),
        workstream_override=WorkstreamDomain.FINANCIAL_QOE,
    ),
    HeuristicIssueRule(
        title="Single-site or capacity concentration risk",
        severity=FlagSeverity.MEDIUM,
        business_impact=(
            "Single-plant dependence or sustained capacity bottlenecks can impair "
            "continuity, delivery performance, and growth capacity."
        ),
        recommended_action=(
            "Review plant-level utilisation, downtime history, alternate-site options, "
            "and contingency planning."
        ),
        patterns=("single plant", "single facility", "capacity bottleneck", "plant shutdown"),
        workstream_override=WorkstreamDomain.OPERATIONS,
    ),
    HeuristicIssueRule(
        title="Supplier concentration or raw-material dependency risk",
        severity=FlagSeverity.MEDIUM,
        business_impact=(
            "Single-source supplier dependence or raw-material shortages can create "
            "margin compression and production disruption."
        ),
        recommended_action=(
            "Quantify supplier concentration, substitution ability, inventory buffers, "
            "and pass-through protections."
        ),
        patterns=(
            "supplier concentration",
            "single supplier",
            "sole supplier",
            "raw material shortage",
        ),
        workstream_override=WorkstreamDomain.OPERATIONS,
    ),
    HeuristicIssueRule(
        title="RBI registration or supervisory exposure",
        severity=FlagSeverity.HIGH,
        business_impact=(
            "Registration gaps or supervisory action can impair product continuity, "
            "investor confidence, and regulatory standing."
        ),
        recommended_action=(
            "Validate registration status, inspection findings, remediation plan, and "
            "any operating restrictions before sign-off."
        ),
        patterns=(
            "certificate of registration",
            "rbi inspection",
            "licence cancelled",
            "supervisory action",
        ),
        workstream_override=WorkstreamDomain.REGULATORY,
    ),
    HeuristicIssueRule(
        title="Asset-quality or provisioning deterioration",
        severity=FlagSeverity.HIGH,
        business_impact=(
            "Weak asset quality or provisioning shortfalls can reduce capital, distort "
            "earnings quality, and increase loss expectations."
        ),
        recommended_action=(
            "Review vintage delinquency, stage migration, provisioning coverage, and "
            "management overlays across key product cohorts."
        ),
        patterns=("gnpa", "nnpa", "stage 3", "provision shortfall", "credit cost spike"),
        workstream_override=WorkstreamDomain.FINANCIAL_QOE,
    ),
    HeuristicIssueRule(
        title="ALM or liquidity mismatch risk",
        severity=FlagSeverity.HIGH,
        business_impact=(
            "Funding mismatches or liquidity stress can constrain growth, elevate "
            "refinancing risk, and trigger regulatory concern."
        ),
        recommended_action=(
            "Assess maturity gaps, buffer adequacy, borrowing concentration, and "
            "contingency funding plans under stress."
        ),
        patterns=(
            "alm mismatch",
            "negative cumulative mismatch",
            "liquidity shortfall",
            "maturity mismatch",
        ),
        workstream_override=WorkstreamDomain.FINANCIAL_QOE,
    ),
    HeuristicIssueRule(
        title="KYC or AML control weakness",
        severity=FlagSeverity.HIGH,
        business_impact=(
            "Weak onboarding or AML controls can create regulatory, fraud, and "
            "reputational exposure for a regulated financial entity."
        ),
        recommended_action=(
            "Review KYC exception logs, AML monitoring backlog, STR governance, and "
            "remediation ownership before approval."
        ),
        patterns=("kyc lapse", "ckyc gap", "suspicious transaction", "aml monitoring backlog"),
        workstream_override=WorkstreamDomain.REGULATORY,
    ),
    HeuristicIssueRule(
        title="Connected lending or evergreening concern",
        severity=FlagSeverity.HIGH,
        business_impact=(
            "Connected lending or evergreening can distort true portfolio quality and "
            "create governance, fraud, and regulatory exposure."
        ),
        recommended_action=(
            "Trace borrower rollovers, connected-party exposure, approval history, and "
            "repayment-source quality for the flagged portfolio."
        ),
        patterns=("evergreening", "connected lending", "evergreen loan", "round tripping loan"),
        workstream_override=WorkstreamDomain.FORENSIC_COMPLIANCE,
    ),
    HeuristicIssueRule(
        title="Collections conduct or outsourcing risk",
        severity=FlagSeverity.MEDIUM,
        business_impact=(
            "Weak collections governance or outsourcing dependence can drive customer "
            "harm, complaints, and regulator attention."
        ),
        recommended_action=(
            "Review call scripts, grievance volumes, collection-agency oversight, and "
            "outsourcing controls for field and digital collections."
        ),
        patterns=(
            "collection agency misconduct",
            "outsourcing dependency",
            "mis-selling complaint",
            "lsp dependency",
        ),
        workstream_override=WorkstreamDomain.OPERATIONS,
    ),
)


class IssueService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.case_service = CaseService(session)

    async def scan_case_evidence(self, case_id: str) -> IssueScanResult | None:
        case = await self.case_service._get_case_record(case_id)
        if case is None:
            return None

        candidates: list[IssueRegisterItemRecord] = []
        fingerprints: set[str] = set()
        for evidence in case.evidence_items:
            candidate = self._candidate_from_evidence(case_id, case.motion_pack, evidence)
            if candidate is None or candidate.fingerprint in fingerprints:
                continue
            fingerprints.add(candidate.fingerprint)
            candidates.append(candidate)

        if not candidates:
            return IssueScanResult(created_count=0, reused_count=0, issues=[])

        existing_result = await self.session.execute(
            select(IssueRegisterItemRecord).where(
                IssueRegisterItemRecord.fingerprint.in_(
                    [candidate.fingerprint for candidate in candidates]
                )
            )
        )
        existing_records = existing_result.scalars().all()
        existing_by_fingerprint = {record.fingerprint: record for record in existing_records}

        created_records: list[IssueRegisterItemRecord] = []
        for candidate in candidates:
            if candidate.fingerprint in existing_by_fingerprint:
                continue
            created_records.append(candidate)

        if created_records:
            self.session.add_all(created_records)
            await self.session.commit()

        all_records = [*created_records, *existing_records]
        return IssueScanResult(
            created_count=len(created_records),
            reused_count=len(existing_records),
            issues=[IssueRegisterItemSummary.model_validate(record) for record in all_records],
        )

    def _candidate_from_evidence(
        self,
        case_id: str,
        motion_pack: str,
        evidence: EvidenceNodeRecord,
    ) -> IssueRegisterItemRecord | None:
        haystack = " ".join(
            filter(None, [evidence.title, evidence.citation, evidence.excerpt])
        ).lower()
        matched_rule = next(
            (
                rule
                for rule in HEURISTIC_RULES
                if rule.motion_packs is None or MotionPack(motion_pack) in rule.motion_packs
                if any(
                    re.search(r"\b" + re.escape(pattern) + r"\b", haystack, re.IGNORECASE)
                    for pattern in rule.patterns
                )
            ),
            None,
        )

        if matched_rule is None and evidence.evidence_kind != "risk":
            return None

        if matched_rule is None:
            title = f"Risk signal: {evidence.title}"
            severity = FlagSeverity.MEDIUM
            business_impact = (
                "A risk-tagged evidence item needs reviewer triage before the case can be "
                "signed off."
            )
            recommended_action = (
                "Confirm the impact, request supporting records, and assign an owner."
            )
            workstream_domain = WorkstreamDomain(evidence.workstream_domain)
        else:
            title = matched_rule.title
            severity = matched_rule.severity
            business_impact = matched_rule.business_impact
            recommended_action = matched_rule.recommended_action
            workstream_domain = matched_rule.workstream_override or WorkstreamDomain(
                evidence.workstream_domain
            )

        fingerprint = hashlib.sha256(
            "|".join([case_id, evidence.id, title, severity.value]).encode("utf-8")
        ).hexdigest()
        return IssueRegisterItemRecord(
            case_id=case_id,
            source_evidence_id=evidence.id,
            title=title,
            summary=evidence.excerpt,
            severity=severity.value,
            status=IssueStatus.OPEN.value,
            workstream_domain=workstream_domain.value,
            business_impact=business_impact,
            recommended_action=recommended_action,
            confidence=min(max(evidence.confidence, 0.55), 0.95),
            fingerprint=fingerprint,
        )
