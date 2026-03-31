from __future__ import annotations

import asyncio
from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    UploadFile,
    status,
)
from fastapi.responses import Response
from starlette.responses import StreamingResponse

from crewai_enterprise_pipeline_api.api.dependencies import DbSession
from crewai_enterprise_pipeline_api.api.security import (
    require_read_access,
    require_reviewer_access,
    require_write_access,
)
from crewai_enterprise_pipeline_api.domain.models import (
    ApprovalDecisionCreate,
    ApprovalDecisionSummary,
    ArtifactSourceKind,
    CaseCreate,
    CaseDetail,
    CaseSummary,
    CaseUpdate,
    ChecklistCoverageSummary,
    ChecklistItemCreate,
    ChecklistItemSummary,
    ChecklistItemUpdate,
    ChecklistSeedResult,
    ChunkSummary,
    ComplianceMatrixItem,
    DocumentArtifactCreate,
    DocumentArtifactSummary,
    DocumentIngestionResult,
    EvidenceConflict,
    EvidenceItemCreate,
    EvidenceItemSummary,
    EvidenceItemUpdate,
    EvidenceKind,
    EvidenceSearchResponse,
    ExecutiveMemoReport,
    FinancialMetricSummary,
    IssueRegisterItemCreate,
    IssueRegisterItemSummary,
    IssueScanResult,
    IssueUpdate,
    LegalStructureSummary,
    QaItemCreate,
    QaItemSummary,
    QaItemUpdate,
    RequestItemCreate,
    RequestItemSummary,
    RequestItemUpdate,
    RunExportPackageCreate,
    RunExportPackageSummary,
    SearchRequest,
    TaxComplianceSummary,
    WorkflowRunCreate,
    WorkflowRunDetail,
    WorkflowRunEnqueueResult,
    WorkflowRunResult,
    WorkflowRunStatus,
    WorkflowRunSummary,
    WorkstreamDomain,
)
from crewai_enterprise_pipeline_api.services.approval_service import ApprovalService
from crewai_enterprise_pipeline_api.services.case_service import CaseService
from crewai_enterprise_pipeline_api.services.checklist_service import ChecklistService
from crewai_enterprise_pipeline_api.services.export_service import ExportService
from crewai_enterprise_pipeline_api.services.financial_qoe_service import FinancialQoEService
from crewai_enterprise_pipeline_api.services.ingestion_service import IngestionService
from crewai_enterprise_pipeline_api.services.issue_service import IssueService
from crewai_enterprise_pipeline_api.services.legal_service import LegalService
from crewai_enterprise_pipeline_api.services.regulatory_service import RegulatoryService
from crewai_enterprise_pipeline_api.services.report_service import ReportService
from crewai_enterprise_pipeline_api.services.search_service import SearchService
from crewai_enterprise_pipeline_api.services.tax_service import TaxService
from crewai_enterprise_pipeline_api.services.workflow_service import WorkflowService
from crewai_enterprise_pipeline_api.storage.service import DocumentStorageService

router = APIRouter(dependencies=[Depends(require_read_access)])


# ---------------------------------------------------------------------------
# Cases
# ---------------------------------------------------------------------------


@router.get("", response_model=list[CaseSummary])
async def list_cases(
    session: DbSession,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
) -> list[CaseSummary]:
    return await CaseService(session).list_cases(skip=skip, limit=limit)


@router.post(
    "",
    response_model=CaseDetail,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_write_access)],
)
async def create_case(payload: CaseCreate, session: DbSession) -> CaseDetail:
    return await CaseService(session).create_case(payload)


@router.get("/{case_id}", response_model=CaseDetail)
async def get_case(case_id: str, session: DbSession) -> CaseDetail:
    case = await CaseService(session).get_case(case_id)
    if case is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")
    return case


@router.patch(
    "/{case_id}",
    response_model=CaseDetail,
    dependencies=[Depends(require_write_access)],
)
async def update_case(
    case_id: str,
    payload: CaseUpdate,
    session: DbSession,
) -> CaseDetail:
    case = await CaseService(session).update_case(case_id, payload)
    if case is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")
    return case


@router.delete(
    "/{case_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_write_access)],
)
async def delete_case(case_id: str, session: DbSession) -> Response:
    deleted = await CaseService(session).delete_case(case_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# Documents
# ---------------------------------------------------------------------------


@router.get("/{case_id}/documents", response_model=list[DocumentArtifactSummary])
async def list_documents(case_id: str, session: DbSession) -> list[DocumentArtifactSummary]:
    return await CaseService(session).list_documents(case_id)


@router.post(
    "/{case_id}/documents",
    response_model=DocumentArtifactSummary,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_write_access)],
)
async def create_document(
    case_id: str,
    payload: DocumentArtifactCreate,
    session: DbSession,
) -> DocumentArtifactSummary:
    artifact = await CaseService(session).add_document(case_id, payload)
    if artifact is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")
    return artifact


@router.get("/{case_id}/documents/{doc_id}", response_model=DocumentArtifactSummary)
async def get_document(
    case_id: str,
    doc_id: str,
    session: DbSession,
) -> DocumentArtifactSummary:
    doc = await CaseService(session).get_document(case_id, doc_id)
    if doc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return doc


@router.delete(
    "/{case_id}/documents/{doc_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_write_access)],
)
async def delete_document(case_id: str, doc_id: str, session: DbSession) -> Response:
    deleted = await CaseService(session).delete_document(case_id, doc_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/{case_id}/documents/{doc_id}/chunks",
    response_model=list[ChunkSummary],
)
async def list_chunks(
    case_id: str,
    doc_id: str,
    session: DbSession,
    skip: int = Query(0, ge=0),
    limit: int = Query(200, ge=1, le=1000),
) -> list[ChunkSummary]:
    chunks = await CaseService(session).list_chunks(case_id, doc_id, skip=skip, limit=limit)
    if chunks is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return chunks


@router.post(
    "/{case_id}/documents/upload",
    response_model=DocumentIngestionResult,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_write_access)],
)
async def upload_document(
    case_id: str,
    session: DbSession,
    file: Annotated[UploadFile, File(...)],
    document_kind: Annotated[str, Form(...)],
    source_kind: Annotated[ArtifactSourceKind, Form(...)],
    workstream_domain: Annotated[WorkstreamDomain, Form(...)],
    title: Annotated[str | None, Form()] = None,
    evidence_kind: Annotated[EvidenceKind, Form()] = EvidenceKind.FACT,
) -> DocumentIngestionResult:
    result = await IngestionService(session).upload_document(
        case_id=case_id,
        file=file,
        document_kind=document_kind,
        source_kind=source_kind,
        workstream_domain=workstream_domain,
        title=title,
        evidence_kind=evidence_kind,
    )
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")
    return result


@router.get(
    "/{case_id}/financial-summary",
    response_model=FinancialMetricSummary,
)
async def get_financial_summary(
    case_id: str,
    session: DbSession,
    persist_checklist: bool = Query(
        True,
        description=(
            "When true, checklist items satisfied by the parsed financial package "
            "are updated before the summary is returned."
        ),
    ),
) -> FinancialMetricSummary:
    summary = await FinancialQoEService(session).build_financial_summary(
        case_id,
        persist_checklist=persist_checklist,
    )
    if summary is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")
    return summary


@router.get(
    "/{case_id}/legal-summary",
    response_model=LegalStructureSummary,
)
async def get_legal_summary(
    case_id: str,
    session: DbSession,
    persist_checklist: bool = Query(
        True,
        description=(
            "When true, checklist items satisfied by the legal engine are updated "
            "before the summary is returned."
        ),
    ),
) -> LegalStructureSummary:
    summary = await LegalService(session).build_legal_summary(
        case_id,
        persist_checklist=persist_checklist,
    )
    if summary is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")
    return summary


@router.get(
    "/{case_id}/tax-summary",
    response_model=TaxComplianceSummary,
)
async def get_tax_summary(
    case_id: str,
    session: DbSession,
    persist_checklist: bool = Query(
        True,
        description=(
            "When true, checklist items satisfied by the tax engine are updated "
            "before the summary is returned."
        ),
    ),
) -> TaxComplianceSummary:
    summary = await TaxService(session).build_tax_summary(
        case_id,
        persist_checklist=persist_checklist,
    )
    if summary is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")
    return summary


@router.get(
    "/{case_id}/compliance-matrix",
    response_model=list[ComplianceMatrixItem],
)
async def get_compliance_matrix(
    case_id: str,
    session: DbSession,
    persist_checklist: bool = Query(
        True,
        description=(
            "When true, checklist items satisfied by the regulatory engine are "
            "updated before the compliance matrix is returned."
        ),
    ),
) -> list[ComplianceMatrixItem]:
    summary = await RegulatoryService(session).build_compliance_matrix(
        case_id,
        persist_checklist=persist_checklist,
    )
    if summary is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")
    return summary.items


# ---------------------------------------------------------------------------
# Evidence
# ---------------------------------------------------------------------------


@router.get("/{case_id}/evidence", response_model=list[EvidenceItemSummary])
async def list_evidence(case_id: str, session: DbSession) -> list[EvidenceItemSummary]:
    return await CaseService(session).list_evidence(case_id)


@router.get(
    "/{case_id}/evidence/conflicts",
    response_model=list[EvidenceConflict],
)
async def detect_evidence_conflicts(
    case_id: str,
    session: DbSession,
) -> list[EvidenceConflict]:
    return await SearchService(session).detect_conflicts(case_id)


@router.post(
    "/{case_id}/evidence",
    response_model=EvidenceItemSummary,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_write_access)],
)
async def create_evidence(
    case_id: str,
    payload: EvidenceItemCreate,
    session: DbSession,
) -> EvidenceItemSummary:
    evidence = await CaseService(session).add_evidence(case_id, payload)
    if evidence is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")
    return evidence


@router.get("/{case_id}/evidence/{evidence_id}", response_model=EvidenceItemSummary)
async def get_evidence(
    case_id: str,
    evidence_id: str,
    session: DbSession,
) -> EvidenceItemSummary:
    evidence = await CaseService(session).get_evidence(case_id, evidence_id)
    if evidence is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Evidence not found"
        )
    return evidence


@router.patch(
    "/{case_id}/evidence/{evidence_id}",
    response_model=EvidenceItemSummary,
    dependencies=[Depends(require_write_access)],
)
async def update_evidence(
    case_id: str,
    evidence_id: str,
    payload: EvidenceItemUpdate,
    session: DbSession,
) -> EvidenceItemSummary:
    evidence = await CaseService(session).update_evidence(case_id, evidence_id, payload)
    if evidence is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Evidence not found"
        )
    return evidence


# ---------------------------------------------------------------------------
# Issues
# ---------------------------------------------------------------------------


@router.get("/{case_id}/issues", response_model=list[IssueRegisterItemSummary])
async def list_issues(case_id: str, session: DbSession) -> list[IssueRegisterItemSummary]:
    return await CaseService(session).list_issues(case_id)


@router.post(
    "/{case_id}/issues",
    response_model=IssueRegisterItemSummary,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_write_access)],
)
async def create_issue(
    case_id: str,
    payload: IssueRegisterItemCreate,
    session: DbSession,
) -> IssueRegisterItemSummary:
    issue = await CaseService(session).add_issue(case_id, payload)
    if issue is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")
    return issue


@router.get("/{case_id}/issues/{issue_id}", response_model=IssueRegisterItemSummary)
async def get_issue(
    case_id: str,
    issue_id: str,
    session: DbSession,
) -> IssueRegisterItemSummary:
    issue = await CaseService(session).get_issue(case_id, issue_id)
    if issue is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Issue not found")
    return issue


@router.patch(
    "/{case_id}/issues/{issue_id}",
    response_model=IssueRegisterItemSummary,
    dependencies=[Depends(require_write_access)],
)
async def update_issue(
    case_id: str,
    issue_id: str,
    payload: IssueUpdate,
    session: DbSession,
) -> IssueRegisterItemSummary:
    issue = await CaseService(session).update_issue(case_id, issue_id, payload)
    if issue is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Issue not found")
    return issue


@router.delete(
    "/{case_id}/issues/{issue_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_write_access)],
)
async def delete_issue(case_id: str, issue_id: str, session: DbSession) -> Response:
    deleted = await CaseService(session).delete_issue(case_id, issue_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Issue not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{case_id}/issues/scan",
    response_model=IssueScanResult,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_write_access)],
)
async def scan_issues(case_id: str, session: DbSession) -> IssueScanResult:
    result = await IssueService(session).scan_case_evidence(case_id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")
    return result


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------


@router.post(
    "/{case_id}/search",
    response_model=EvidenceSearchResponse,
)
async def search_evidence(
    case_id: str,
    payload: SearchRequest,
    session: DbSession,
) -> EvidenceSearchResponse:
    return await SearchService(session).hybrid_search(case_id, payload)


# ---------------------------------------------------------------------------
# Checklist
# ---------------------------------------------------------------------------


@router.get("/{case_id}/checklist", response_model=list[ChecklistItemSummary])
async def list_checklist_items(
    case_id: str,
    session: DbSession,
) -> list[ChecklistItemSummary]:
    return await CaseService(session).list_checklist_items(case_id)


@router.post(
    "/{case_id}/checklist",
    response_model=ChecklistItemSummary,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_write_access)],
)
async def create_checklist_item(
    case_id: str,
    payload: ChecklistItemCreate,
    session: DbSession,
) -> ChecklistItemSummary:
    item = await CaseService(session).add_checklist_item(case_id, payload)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")
    return item


@router.patch(
    "/{case_id}/checklist/{item_id}",
    response_model=ChecklistItemSummary,
    dependencies=[Depends(require_write_access)],
)
async def update_checklist_item(
    case_id: str,
    item_id: str,
    payload: ChecklistItemUpdate,
    session: DbSession,
) -> ChecklistItemSummary:
    item = await CaseService(session).update_checklist_item(case_id, item_id, payload)
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Checklist item not found",
        )
    return item


@router.post(
    "/{case_id}/checklist/seed",
    response_model=ChecklistSeedResult,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_write_access)],
)
async def seed_checklist(case_id: str, session: DbSession) -> ChecklistSeedResult:
    result = await ChecklistService(session).seed_case_checklist(case_id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")
    return result


@router.get("/{case_id}/coverage", response_model=ChecklistCoverageSummary)
async def get_coverage(case_id: str, session: DbSession) -> ChecklistCoverageSummary:
    summary = await ChecklistService(session).get_coverage_summary(case_id)
    if summary is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")
    return summary


# ---------------------------------------------------------------------------
# Approvals
# ---------------------------------------------------------------------------


@router.get("/{case_id}/approvals", response_model=list[ApprovalDecisionSummary])
async def list_approvals(
    case_id: str,
    session: DbSession,
) -> list[ApprovalDecisionSummary]:
    return await CaseService(session).list_approvals(case_id)


@router.post(
    "/{case_id}/approvals/review",
    response_model=ApprovalDecisionSummary,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_reviewer_access)],
)
async def review_case(
    case_id: str,
    payload: ApprovalDecisionCreate,
    session: DbSession,
) -> ApprovalDecisionSummary:
    decision = await ApprovalService(session).review_case(case_id, payload)
    if decision is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")
    return decision


# ---------------------------------------------------------------------------
# Reports
# ---------------------------------------------------------------------------


@router.get(
    "/{case_id}/reports/executive-memo",
    response_model=ExecutiveMemoReport,
)
async def get_executive_memo(
    case_id: str,
    session: DbSession,
) -> ExecutiveMemoReport:
    report = await ReportService(session).build_executive_memo(case_id)
    if report is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")
    return report


# ---------------------------------------------------------------------------
# Requests
# ---------------------------------------------------------------------------


@router.get("/{case_id}/requests", response_model=list[RequestItemSummary])
async def list_requests(case_id: str, session: DbSession) -> list[RequestItemSummary]:
    return await CaseService(session).list_requests(case_id)


@router.post(
    "/{case_id}/requests",
    response_model=RequestItemSummary,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_write_access)],
)
async def create_request_item(
    case_id: str,
    payload: RequestItemCreate,
    session: DbSession,
) -> RequestItemSummary:
    request_item = await CaseService(session).add_request_item(case_id, payload)
    if request_item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")
    return request_item


@router.patch(
    "/{case_id}/requests/{item_id}",
    response_model=RequestItemSummary,
    dependencies=[Depends(require_write_access)],
)
async def update_request_item(
    case_id: str,
    item_id: str,
    payload: RequestItemUpdate,
    session: DbSession,
) -> RequestItemSummary:
    item = await CaseService(session).update_request_item(case_id, item_id, payload)
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Request item not found"
        )
    return item


# ---------------------------------------------------------------------------
# Q&A
# ---------------------------------------------------------------------------


@router.get("/{case_id}/qa", response_model=list[QaItemSummary])
async def list_qa_items(case_id: str, session: DbSession) -> list[QaItemSummary]:
    return await CaseService(session).list_qa_items(case_id)


@router.post(
    "/{case_id}/qa",
    response_model=QaItemSummary,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_write_access)],
)
async def create_qa_item(
    case_id: str,
    payload: QaItemCreate,
    session: DbSession,
) -> QaItemSummary:
    qa_item = await CaseService(session).add_qa_item(case_id, payload)
    if qa_item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")
    return qa_item


@router.patch(
    "/{case_id}/qa/{item_id}",
    response_model=QaItemSummary,
    dependencies=[Depends(require_write_access)],
)
async def update_qa_item(
    case_id: str,
    item_id: str,
    payload: QaItemUpdate,
    session: DbSession,
) -> QaItemSummary:
    item = await CaseService(session).update_qa_item(case_id, item_id, payload)
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Q&A item not found"
        )
    return item


# ---------------------------------------------------------------------------
# Workflow Runs
# ---------------------------------------------------------------------------


@router.get("/{case_id}/runs", response_model=list[WorkflowRunSummary])
async def list_runs(case_id: str, session: DbSession) -> list[WorkflowRunSummary]:
    return await WorkflowService(session).list_runs(case_id)


@router.post(
    "/{case_id}/runs",
    response_model=WorkflowRunResult | WorkflowRunEnqueueResult,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_write_access)],
)
async def execute_run(
    case_id: str,
    payload: WorkflowRunCreate,
    session: DbSession,
    request: Request,
) -> WorkflowRunResult | WorkflowRunEnqueueResult:
    service = WorkflowService(session)
    redis_pool = getattr(request.app.state, "redis_pool", None)
    if redis_pool is not None:
        result = await service.enqueue_run(case_id, payload, redis_pool)
        if result is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")
        return result

    result = await service.execute_run(case_id, payload)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")
    return result


@router.get("/{case_id}/runs/{run_id}", response_model=WorkflowRunDetail)
async def get_run(
    case_id: str,
    run_id: str,
    session: DbSession,
) -> WorkflowRunDetail:
    run = await WorkflowService(session).get_run(case_id, run_id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")
    return run


@router.get("/{case_id}/runs/{run_id}/stream")
async def stream_run_progress(
    case_id: str,
    run_id: str,
    session: DbSession,
) -> StreamingResponse:
    """SSE endpoint that polls run status and streams trace events.

    Emits ``event: trace`` for each new trace event and ``event: status``
    when the run status changes.  Closes the stream once the run reaches
    a terminal state (completed / failed).
    """

    async def _event_generator():
        last_event_count = 0
        last_status: str | None = None

        while True:
            run = await WorkflowService(session).get_run(case_id, run_id)
            if run is None:
                yield f"event: error\ndata: Run {run_id} not found\n\n"
                return

            if run.status.value != last_status:
                last_status = run.status.value
                yield f"event: status\ndata: {last_status}\n\n"

            events = run.trace_events
            if len(events) > last_event_count:
                for evt in events[last_event_count:]:
                    import json

                    payload = json.dumps(
                        {
                            "sequence_number": evt.sequence_number,
                            "step_key": evt.step_key,
                            "title": evt.title,
                            "message": evt.message,
                            "level": evt.level.value,
                        }
                    )
                    yield f"event: trace\ndata: {payload}\n\n"
                last_event_count = len(events)

            if run.status in (WorkflowRunStatus.COMPLETED, WorkflowRunStatus.FAILED):
                yield "event: done\ndata: stream closed\n\n"
                return

            await asyncio.sleep(1)

    return StreamingResponse(
        _event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post(
    "/{case_id}/runs/{run_id}/export-package",
    response_model=RunExportPackageSummary,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_write_access)],
)
async def create_run_export_package(
    case_id: str,
    run_id: str,
    payload: RunExportPackageCreate,
    session: DbSession,
) -> RunExportPackageSummary:
    export_package = await ExportService(session).create_run_export_package(
        case_id,
        run_id,
        payload,
    )
    if export_package is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")
    return export_package


@router.get(
    "/{case_id}/runs/{run_id}/export-packages/{package_id}/download",
)
async def download_export_package(
    case_id: str,
    run_id: str,
    package_id: str,
    session: DbSession,
) -> Response:
    from sqlalchemy import select

    from crewai_enterprise_pipeline_api.db.models import RunExportPackageRecord

    result = await session.execute(
        select(RunExportPackageRecord).where(
            RunExportPackageRecord.id == package_id,
            RunExportPackageRecord.case_id == case_id,
            RunExportPackageRecord.run_id == run_id,
        )
    )
    record = result.scalar_one_or_none()
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Export package not found"
        )

    storage = DocumentStorageService()
    content = storage.retrieve_bytes(record.storage_path)
    if content is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Export package file not found in storage",
        )

    return Response(
        content=content,
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{record.file_name}"',
            "Content-Length": str(len(content)),
        },
    )
