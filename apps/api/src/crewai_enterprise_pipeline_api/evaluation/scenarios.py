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
            "note": "Automated quality-gate review for the first flagship slice.",
        }
    )
    run_payload: dict[str, Any] = field(
        default_factory=lambda: {
            "requested_by": "Evaluation Runner",
            "note": "Automated run for the phase-five quality gate.",
        }
    )
    expectation: ScenarioExpectation = field(
        default_factory=lambda: ScenarioExpectation(
            approval_decision="changes_requested",
            ready_for_export=False,
            report_status="not_ready",
        )
    )


PHASE5_FIRST_SLICE_SCENARIOS: tuple[EvaluationScenario, ...] = (
    EvaluationScenario(
        code="blocked_tax_notice_case",
        name="Blocked tax notice case",
        description=(
            "Validates that open mandatory checklist items plus a high-severity GST issue "
            "keep the case out of export-ready status."
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
                    "74 percent after cloud spend optimisation. No tax notices or litigation "
                    "matters were reported in the period."
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
                    "detail": "Need renewal history, pricing protections, and churn sensitivity.",
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
