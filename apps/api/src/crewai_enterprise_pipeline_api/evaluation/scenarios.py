from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class UploadDocumentFixture:
    title: str
    filename: str
    content: str
    mime_type: str
    document_kind: str
    source_kind: str
    workstream_domain: str
    evidence_kind: str = "fact"


@dataclass(slots=True)
class EvidenceFixture:
    payload: dict[str, Any]


@dataclass(slots=True)
class IssueFixture:
    payload: dict[str, Any]


@dataclass(slots=True)
class RequestFixture:
    payload: dict[str, Any]


@dataclass(slots=True)
class QaFixture:
    payload: dict[str, Any]


@dataclass(slots=True)
class ChecklistUpdateFixture:
    template_key: str
    payload: dict[str, Any]


@dataclass(slots=True)
class ScenarioExpectation:
    approval_decision: str
    ready_for_export: bool
    report_status: str
    report_title: str | None = None
    open_mandatory_items: int | None = None
    min_blocking_issue_count: int | None = None
    max_blocking_issue_count: int | None = None
    min_trace_events: int = 6
    min_report_bundles: int = 3
    min_syntheses: int = 8
    min_issue_count: int = 0
    min_open_request_count: int = 0
    min_evidence_count: int = 1
    expected_issue_severities: tuple[str, ...] = ()
    expected_bundle_kinds: tuple[str, ...] = (
        "executive_memo_markdown",
        "issue_register_markdown",
        "workstream_synthesis_markdown",
    )


@dataclass(slots=True)
class EvaluationScenario:
    code: str
    name: str
    description: str
    case_payload: dict[str, Any]
    upload_documents: tuple[UploadDocumentFixture, ...] = ()
    evidence_items: tuple[EvidenceFixture, ...] = ()
    issues: tuple[IssueFixture, ...] = ()
    requests: tuple[RequestFixture, ...] = ()
    qa_items: tuple[QaFixture, ...] = ()
    checklist_updates: tuple[ChecklistUpdateFixture, ...] = ()
    satisfy_all_checklist_items: bool = False
    scan_issues: bool = False
    approval_payload: dict[str, Any] = field(
        default_factory=lambda: {
            "reviewer": "Evaluation Reviewer",
            "note": "Automated quality-gate review for the current suite.",
        }
    )
    run_payload: dict[str, Any] = field(
        default_factory=lambda: {
            "requested_by": "Evaluation Runner",
            "note": "Automated run for the current evaluation suite.",
        }
    )
    expectation: ScenarioExpectation = field(
        default_factory=lambda: ScenarioExpectation(
            approval_decision="changes_requested",
            ready_for_export=False,
            report_status="not_ready",
        )
    )


@dataclass(frozen=True, slots=True)
class EvaluationSuiteDefinition:
    key: str
    title: str
    artifact_prefix: str
    scenarios: tuple[EvaluationScenario, ...]


PHASE5_FIRST_SLICE_SCENARIOS: tuple[EvaluationScenario, ...] = (
    EvaluationScenario(
        code="blocked_tax_notice_case",
        name="Blocked tax notice case",
        description=(
            "Validates that open mandatory checklist items plus a high-severity GST "
            "issue keep the case out of export-ready status."
        ),
        case_payload={
            "name": "Project Banyan",
            "target_name": "Banyan Cloud Private Limited",
            "summary": "Evaluation scenario for blocked tax diligence readiness.",
            "motion_pack": "buy_side_diligence",
            "sector_pack": "tech_saas_services",
            "country": "India",
        },
        upload_documents=(
            UploadDocumentFixture(
                title="GST notice pack",
                filename="gst_notice_pack.txt",
                content=(
                    "The company received a GST notice seeking additional tax demand "
                    "for input credit reversals in Maharashtra and Karnataka."
                ),
                mime_type="text/plain",
                document_kind="tax_notice_pack",
                source_kind="uploaded_dataroom",
                workstream_domain="tax",
                evidence_kind="risk",
            ),
        ),
        requests=(
            RequestFixture(
                payload={
                    "title": "Upload GST demand responses",
                    "detail": "Need show-cause replies, challans, and counsel assessment.",
                    "owner": "Tax Controller",
                    "status": "open",
                }
            ),
        ),
        qa_items=(
            QaFixture(
                payload={
                    "question": "Why was input credit reversed across two states?",
                    "requested_by": "Tax workstream",
                    "response": "Management is reconciling vendor classifications with advisors.",
                    "status": "answered",
                }
            ),
        ),
        scan_issues=True,
        expectation=ScenarioExpectation(
            approval_decision="changes_requested",
            ready_for_export=False,
            report_status="not_ready",
            report_title="Executive Memo",
            open_mandatory_items=10,
            min_blocking_issue_count=1,
            max_blocking_issue_count=1,
            min_issue_count=1,
            min_open_request_count=1,
            min_evidence_count=1,
            expected_issue_severities=("high",),
        ),
    ),
    EvaluationScenario(
        code="clean_approved_case",
        name="Clean approved case",
        description=(
            "Validates that a fully satisfied checklist with no open blocking issues "
            "produces an approved, export-ready diligence state."
        ),
        case_payload={
            "name": "Project Marigold",
            "target_name": "Marigold Software Private Limited",
            "summary": "Evaluation scenario for an export-ready clean diligence case.",
            "motion_pack": "buy_side_diligence",
            "sector_pack": "tech_saas_services",
            "country": "India",
        },
        upload_documents=(
            UploadDocumentFixture(
                title="Audited finance summary",
                filename="audited_finance_summary.txt",
                content=(
                    "Revenue grew 29 percent year over year. Gross margin improved to "
                    "74 percent after cloud spend optimisation. No tax notices or "
                    "litigation matters were reported in the period."
                ),
                mime_type="text/plain",
                document_kind="audited_financials",
                source_kind="uploaded_dataroom",
                workstream_domain="financial_qoe",
                evidence_kind="metric",
            ),
        ),
        evidence_items=(
            EvidenceFixture(
                payload={
                    "title": "Customer retention summary",
                    "evidence_kind": "metric",
                    "workstream_domain": "commercial",
                    "citation": "Commercial KPI pack FY25",
                    "excerpt": (
                        "Gross revenue retention remained above 96 percent across the "
                        "last 24 months."
                    ),
                    "confidence": 0.88,
                }
            ),
        ),
        qa_items=(
            QaFixture(
                payload={
                    "question": "Have all board approvals for ESOP grants been reconciled?",
                    "requested_by": "Legal workstream",
                    "response": (
                        "Yes, cap table and board minutes were matched to the ESOP "
                        "register."
                    ),
                    "status": "answered",
                }
            ),
        ),
        satisfy_all_checklist_items=True,
        expectation=ScenarioExpectation(
            approval_decision="approved",
            ready_for_export=True,
            report_status="ready_for_export",
            report_title="Executive Memo",
            open_mandatory_items=0,
            min_blocking_issue_count=0,
            max_blocking_issue_count=0,
            min_issue_count=0,
            min_open_request_count=0,
            min_evidence_count=2,
        ),
    ),
    EvaluationScenario(
        code="approved_nonblocking_concentration_case",
        name="Approved non-blocking concentration case",
        description=(
            "Validates the current first-slice policy that a medium-severity commercial "
            "issue can still be approved if mandatory coverage is complete."
        ),
        case_payload={
            "name": "Project Saffron",
            "target_name": "Saffron Workflow Systems Private Limited",
            "summary": "Evaluation scenario for a non-blocking commercial concentration risk.",
            "motion_pack": "buy_side_diligence",
            "sector_pack": "tech_saas_services",
            "country": "India",
        },
        upload_documents=(
            UploadDocumentFixture(
                title="Customer concentration note",
                filename="customer_concentration_note.txt",
                content=(
                    "Customer concentration remains elevated because one top customer "
                    "contributes 38 percent of ARR under a renewal due next quarter."
                ),
                mime_type="text/plain",
                document_kind="commercial_kpi_pack",
                source_kind="uploaded_dataroom",
                workstream_domain="commercial",
                evidence_kind="risk",
            ),
        ),
        requests=(
            RequestFixture(
                payload={
                    "title": "Share top-customer renewal deck",
                    "detail": (
                        "Need renewal history, pricing protections, and churn "
                        "sensitivity."
                    ),
                    "owner": "Commercial Lead",
                    "status": "open",
                }
            ),
        ),
        checklist_updates=(
            ChecklistUpdateFixture(
                template_key="commercial.customer_concentration",
                payload={
                    "status": "satisfied",
                    "owner": "Commercial Lead",
                    "note": "Concentration analysis updated with current renewal pipeline.",
                },
            ),
        ),
        satisfy_all_checklist_items=True,
        scan_issues=True,
        expectation=ScenarioExpectation(
            approval_decision="approved",
            ready_for_export=True,
            report_status="ready_for_export",
            report_title="Executive Memo",
            open_mandatory_items=0,
            min_blocking_issue_count=0,
            max_blocking_issue_count=0,
            min_issue_count=1,
            min_open_request_count=1,
            min_evidence_count=1,
            expected_issue_severities=("medium",),
        ),
    ),
)


CREDIT_LENDING_EXPANSION_SCENARIOS: tuple[EvaluationScenario, ...] = (
    EvaluationScenario(
        code="blocked_credit_covenant_case",
        name="Blocked credit covenant case",
        description=(
            "Validates that covenant stress and open underwriting items block credit "
            "approval for the credit-lending motion pack."
        ),
        case_payload={
            "name": "Project Monsoon Credit Review",
            "target_name": "Monsoon Commerce Private Limited",
            "summary": "Evaluation scenario for blocked underwriting readiness.",
            "motion_pack": "credit_lending",
            "sector_pack": "tech_saas_services",
            "country": "India",
        },
        upload_documents=(
            UploadDocumentFixture(
                title="Lender monitoring note",
                filename="lender_monitoring_note.txt",
                content=(
                    "The borrower breached a covenant in Q4 and debt service coverage "
                    "fell below the internal threshold. Days past due moved to 38."
                ),
                mime_type="text/plain",
                document_kind="lender_monitoring_note",
                source_kind="uploaded_dataroom",
                workstream_domain="financial_qoe",
                evidence_kind="risk",
            ),
        ),
        requests=(
            RequestFixture(
                payload={
                    "title": "Upload covenant waiver correspondence",
                    "detail": (
                        "Need lender waivers, cure plan, and updated quarterly cash-flow "
                        "forecast."
                    ),
                    "owner": "Treasury Lead",
                    "status": "open",
                }
            ),
        ),
        scan_issues=True,
        expectation=ScenarioExpectation(
            approval_decision="changes_requested",
            ready_for_export=False,
            report_status="not_ready",
            report_title="Credit Memo",
            open_mandatory_items=11,
            min_blocking_issue_count=1,
            max_blocking_issue_count=1,
            min_issue_count=1,
            min_open_request_count=1,
            min_evidence_count=1,
            expected_issue_severities=("high",),
        ),
    ),
    EvaluationScenario(
        code="approved_credit_case",
        name="Approved credit case",
        description=(
            "Validates an approved credit memo path when underwriting checklist "
            "coverage is complete and no blocking credit risks remain open."
        ),
        case_payload={
            "name": "Project Banyan Working Capital Line",
            "target_name": "Banyan Workflow Systems Private Limited",
            "summary": "Evaluation scenario for an approved corporate credit case.",
            "motion_pack": "credit_lending",
            "sector_pack": "tech_saas_services",
            "country": "India",
        },
        upload_documents=(
            UploadDocumentFixture(
                title="Underwriting summary",
                filename="underwriting_summary.txt",
                content=(
                    "Debt service coverage remained above 1.8x, collections were stable, "
                    "and no covenant breach, default, or tax notice was reported."
                ),
                mime_type="text/plain",
                document_kind="underwriting_summary",
                source_kind="uploaded_dataroom",
                workstream_domain="financial_qoe",
                evidence_kind="metric",
            ),
        ),
        evidence_items=(
            EvidenceFixture(
                payload={
                    "title": "Banking behaviour summary",
                    "evidence_kind": "fact",
                    "workstream_domain": "forensic_compliance",
                    "citation": "Borrower bank statement review FY26 Q1",
                    "excerpt": (
                        "Bank statement review did not identify material related-party "
                        "fund diversion or end-use deviation."
                    ),
                    "confidence": 0.87,
                }
            ),
        ),
        satisfy_all_checklist_items=True,
        expectation=ScenarioExpectation(
            approval_decision="approved",
            ready_for_export=True,
            report_status="ready_for_export",
            report_title="Credit Memo",
            open_mandatory_items=0,
            min_blocking_issue_count=0,
            max_blocking_issue_count=0,
            min_issue_count=0,
            min_open_request_count=0,
            min_evidence_count=2,
        ),
    ),
)


VENDOR_ONBOARDING_EXPANSION_SCENARIOS: tuple[EvaluationScenario, ...] = (
    EvaluationScenario(
        code="blocked_vendor_integrity_case",
        name="Blocked vendor integrity case",
        description=(
            "Validates that integrity and sanctions concerns block third-party "
            "approval while onboarding checklist items remain open."
        ),
        case_payload={
            "name": "Project Copper Vendor Onboarding",
            "target_name": "Copper Cloud Services Private Limited",
            "summary": "Evaluation scenario for blocked vendor onboarding readiness.",
            "motion_pack": "vendor_onboarding",
            "sector_pack": "tech_saas_services",
            "country": "India",
        },
        upload_documents=(
            UploadDocumentFixture(
                title="Integrity screening summary",
                filename="integrity_screening_summary.txt",
                content=(
                    "Integrity concern surfaced after an aml alert and sanctions "
                    "watchlist hit involving a beneficial owner."
                ),
                mime_type="text/plain",
                document_kind="integrity_screening",
                source_kind="uploaded_dataroom",
                workstream_domain="forensic_compliance",
                evidence_kind="risk",
            ),
        ),
        requests=(
            RequestFixture(
                payload={
                    "title": "Upload beneficial-owner clarification",
                    "detail": (
                        "Need ownership clarification, screening evidence, and "
                        "compliance sign-off notes."
                    ),
                    "owner": "Third-Party Risk Lead",
                    "status": "open",
                }
            ),
        ),
        scan_issues=True,
        expectation=ScenarioExpectation(
            approval_decision="changes_requested",
            ready_for_export=False,
            report_status="not_ready",
            report_title="Third-Party Risk Memo",
            min_syntheses=7,
            open_mandatory_items=10,
            min_blocking_issue_count=1,
            max_blocking_issue_count=1,
            min_issue_count=1,
            min_open_request_count=1,
            min_evidence_count=1,
            expected_issue_severities=("high",),
        ),
    ),
    EvaluationScenario(
        code="approved_vendor_case",
        name="Approved vendor case",
        description=(
            "Validates an approved vendor onboarding path when checklist coverage is "
            "complete and no blocking third-party risks remain open."
        ),
        case_payload={
            "name": "Project Delta Vendor Approval",
            "target_name": "Delta Automation Services Private Limited",
            "summary": "Evaluation scenario for a clean vendor onboarding case.",
            "motion_pack": "vendor_onboarding",
            "sector_pack": "tech_saas_services",
            "country": "India",
        },
        upload_documents=(
            UploadDocumentFixture(
                title="Vendor profile summary",
                filename="vendor_profile_summary.txt",
                content=(
                    "The vendor maintains current registrations, no sanctions alerts, "
                    "and no integrity or cyber incident red flags were identified."
                ),
                mime_type="text/plain",
                document_kind="vendor_profile",
                source_kind="uploaded_dataroom",
                workstream_domain="legal_corporate",
                evidence_kind="fact",
            ),
        ),
        evidence_items=(
            EvidenceFixture(
                payload={
                    "title": "Security questionnaire summary",
                    "evidence_kind": "fact",
                    "workstream_domain": "cyber_privacy",
                    "citation": "Vendor security questionnaire v3",
                    "excerpt": (
                        "The vendor completed the security questionnaire with no "
                        "material control gaps requiring escalation."
                    ),
                    "confidence": 0.9,
                }
            ),
        ),
        satisfy_all_checklist_items=True,
        expectation=ScenarioExpectation(
            approval_decision="approved",
            ready_for_export=True,
            report_status="ready_for_export",
            report_title="Third-Party Risk Memo",
            min_syntheses=7,
            open_mandatory_items=0,
            min_blocking_issue_count=0,
            max_blocking_issue_count=0,
            min_issue_count=0,
            min_open_request_count=0,
            min_evidence_count=2,
        ),
    ),
)


MANUFACTURING_INDUSTRIALS_EXPANSION_SCENARIOS: tuple[EvaluationScenario, ...] = (
    EvaluationScenario(
        code="blocked_manufacturing_ehs_case",
        name="Blocked manufacturing EHS case",
        description=(
            "Validates that manufacturing-sector red flags and open sector checklist "
            "coverage block buy-side export readiness."
        ),
        case_payload={
            "name": "Project Forge Acquisition",
            "target_name": "Forge Components Private Limited",
            "summary": "Evaluation scenario for blocked manufacturing diligence readiness.",
            "motion_pack": "buy_side_diligence",
            "sector_pack": "manufacturing_industrials",
            "country": "India",
        },
        upload_documents=(
            UploadDocumentFixture(
                title="Environmental compliance note",
                filename="environmental_compliance_note.txt",
                content=(
                    "The plant received an environmental notice from the pollution control "
                    "board and the consent to operate renewal remains pending."
                ),
                mime_type="text/plain",
                document_kind="environmental_compliance_note",
                source_kind="uploaded_dataroom",
                workstream_domain="regulatory",
                evidence_kind="risk",
            ),
            UploadDocumentFixture(
                title="Inventory review note",
                filename="inventory_review_note.txt",
                content=(
                    "Inventory aging increased sharply because obsolete stock and a scrap "
                    "write-off were identified in two product lines."
                ),
                mime_type="text/plain",
                document_kind="inventory_review_note",
                source_kind="uploaded_dataroom",
                workstream_domain="financial_qoe",
                evidence_kind="risk",
            ),
            UploadDocumentFixture(
                title="Supply continuity note",
                filename="supply_continuity_note.txt",
                content=(
                    "Supplier concentration remains elevated because a single supplier "
                    "controls a critical alloy input and a raw material shortage hit the "
                    "plant last quarter."
                ),
                mime_type="text/plain",
                document_kind="supply_continuity_note",
                source_kind="uploaded_dataroom",
                workstream_domain="operations",
                evidence_kind="risk",
            ),
        ),
        requests=(
            RequestFixture(
                payload={
                    "title": "Upload factory licence and remediation tracker",
                    "detail": (
                        "Need consent-to-operate filings, remediation capex plan, and the "
                        "latest EHS action tracker."
                    ),
                    "owner": "Operations Controller",
                    "status": "open",
                }
            ),
        ),
        scan_issues=True,
        expectation=ScenarioExpectation(
            approval_decision="changes_requested",
            ready_for_export=False,
            report_status="not_ready",
            report_title="Executive Memo",
            min_syntheses=7,
            open_mandatory_items=13,
            min_blocking_issue_count=1,
            max_blocking_issue_count=1,
            min_issue_count=3,
            min_open_request_count=1,
            min_evidence_count=3,
            expected_issue_severities=("high", "medium"),
        ),
    ),
    EvaluationScenario(
        code="approved_manufacturing_credit_case",
        name="Approved manufacturing credit case",
        description=(
            "Validates that the manufacturing sector pack composes cleanly with the "
            "credit-lending motion pack."
        ),
        case_payload={
            "name": "Project Alloy Working Capital Line",
            "target_name": "Alloy Motion Systems Private Limited",
            "summary": "Evaluation scenario for an approved manufacturing credit case.",
            "motion_pack": "credit_lending",
            "sector_pack": "manufacturing_industrials",
            "country": "India",
        },
        upload_documents=(
            UploadDocumentFixture(
                title="Manufacturing underwriting summary",
                filename="manufacturing_underwriting_summary.txt",
                content=(
                    "Debt service coverage remained above 2.1x, plant utilisation stayed "
                    "stable, maintenance stayed within plan, and statutory permits were "
                    "current across the review period."
                ),
                mime_type="text/plain",
                document_kind="manufacturing_underwriting_summary",
                source_kind="uploaded_dataroom",
                workstream_domain="financial_qoe",
                evidence_kind="metric",
            ),
        ),
        evidence_items=(
            EvidenceFixture(
                payload={
                    "title": "Plant continuity review",
                    "evidence_kind": "fact",
                    "workstream_domain": "operations",
                    "citation": "Operations review pack FY26 Q1",
                    "excerpt": (
                        "The borrower maintains alternate sourcing for critical inputs and "
                        "documented preventive maintenance across both production shifts."
                    ),
                    "confidence": 0.89,
                }
            ),
        ),
        satisfy_all_checklist_items=True,
        expectation=ScenarioExpectation(
            approval_decision="approved",
            ready_for_export=True,
            report_status="ready_for_export",
            report_title="Credit Memo",
            min_syntheses=7,
            open_mandatory_items=0,
            min_blocking_issue_count=0,
            max_blocking_issue_count=0,
            min_issue_count=0,
            min_open_request_count=0,
            min_evidence_count=2,
        ),
    ),
)


EVALUATION_SUITES: dict[str, EvaluationSuiteDefinition] = {
    "phase5_first_slice": EvaluationSuiteDefinition(
        key="phase5_first_slice",
        title="Phase 5 First Slice Evaluation",
        artifact_prefix="phase5-first-slice",
        scenarios=PHASE5_FIRST_SLICE_SCENARIOS,
    ),
    "credit_lending_expansion": EvaluationSuiteDefinition(
        key="credit_lending_expansion",
        title="Credit Lending Expansion Evaluation",
        artifact_prefix="credit-lending-expansion",
        scenarios=CREDIT_LENDING_EXPANSION_SCENARIOS,
    ),
    "vendor_onboarding_expansion": EvaluationSuiteDefinition(
        key="vendor_onboarding_expansion",
        title="Vendor Onboarding Expansion Evaluation",
        artifact_prefix="vendor-onboarding-expansion",
        scenarios=VENDOR_ONBOARDING_EXPANSION_SCENARIOS,
    ),
    "manufacturing_industrials_expansion": EvaluationSuiteDefinition(
        key="manufacturing_industrials_expansion",
        title="Manufacturing Industrials Expansion Evaluation",
        artifact_prefix="manufacturing-industrials-expansion",
        scenarios=MANUFACTURING_INDUSTRIALS_EXPANSION_SCENARIOS,
    ),
}
