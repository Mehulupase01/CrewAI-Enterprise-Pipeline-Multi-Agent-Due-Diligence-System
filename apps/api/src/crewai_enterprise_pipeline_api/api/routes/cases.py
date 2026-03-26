from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

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
    ChecklistCoverageSummary,
    ChecklistItemCreate,
    ChecklistItemSummary,
    ChecklistItemUpdate,
    ChecklistSeedResult,
    DocumentArtifactCreate,
    DocumentArtifactSummary,
    DocumentIngestionResult,
    EvidenceItemCreate,
    EvidenceItemSummary,
    EvidenceKind,
    ExecutiveMemoReport,
    IssueRegisterItemCreate,
    IssueRegisterItemSummary,
    IssueScanResult,
    QaItemCreate,
    QaItemSummary,
    RequestItemCreate,
    RequestItemSummary,
    RunExportPackageCreate,
    RunExportPackageSummary,
    WorkflowRunCreate,
    WorkflowRunDetail,
    WorkflowRunResult,
    WorkflowRunSummary,
    WorkstreamDomain,
)
from crewai_enterprise_pipeline_api.services.approval_service import ApprovalService
from crewai_enterprise_pipeline_api.services.case_service import CaseService
from crewai_enterprise_pipeline_api.services.checklist_service import ChecklistService
from crewai_enterprise_pipeline_api.services.export_service import ExportService
from crewai_enterprise_pipeline_api.services.ingestion_service import IngestionService
from crewai_enterprise_pipeline_api.services.issue_service import IssueService
from crewai_enterprise_pipeline_api.services.report_service import ReportService
from crewai_enterprise_pipeline_api.services.workflow_service import WorkflowService

router = APIRouter(dependencies=[Depends(require_read_access)])


@router.get("", response_model=list[CaseSummary])
async def list_cases(session: DbSession) -> list[CaseSummary]:
    return await CaseService(session).list_cases()


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


@router.get("/{case_id}/evidence", response_model=list[EvidenceItemSummary])
async def list_evidence(case_id: str, session: DbSession) -> list[EvidenceItemSummary]:
    return await CaseService(session).list_evidence(case_id)


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


@router.get("/{case_id}/runs", response_model=list[WorkflowRunSummary])
async def list_runs(case_id: str, session: DbSession) -> list[WorkflowRunSummary]:
    return await WorkflowService(session).list_runs(case_id)


@router.post(
    "/{case_id}/runs",
    response_model=WorkflowRunResult,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_write_access)],
)
async def execute_run(
    case_id: str,
    payload: WorkflowRunCreate,
    session: DbSession,
) -> WorkflowRunResult:
    result = await WorkflowService(session).execute_run(case_id, payload)
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
