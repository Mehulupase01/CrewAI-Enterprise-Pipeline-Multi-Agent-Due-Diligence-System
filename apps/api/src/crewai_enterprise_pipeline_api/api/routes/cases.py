from fastapi import APIRouter, HTTPException, status

from crewai_enterprise_pipeline_api.api.dependencies import DbSession
from crewai_enterprise_pipeline_api.domain.models import (
    CaseCreate,
    CaseDetail,
    CaseSummary,
    DocumentArtifactCreate,
    DocumentArtifactSummary,
    EvidenceItemCreate,
    EvidenceItemSummary,
    QaItemCreate,
    QaItemSummary,
    RequestItemCreate,
    RequestItemSummary,
)
from crewai_enterprise_pipeline_api.services.case_service import CaseService

router = APIRouter()


@router.get("", response_model=list[CaseSummary])
async def list_cases(session: DbSession) -> list[CaseSummary]:
    return await CaseService(session).list_cases()


@router.post("", response_model=CaseDetail, status_code=status.HTTP_201_CREATED)
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


@router.get("/{case_id}/evidence", response_model=list[EvidenceItemSummary])
async def list_evidence(case_id: str, session: DbSession) -> list[EvidenceItemSummary]:
    return await CaseService(session).list_evidence(case_id)


@router.post(
    "/{case_id}/evidence",
    response_model=EvidenceItemSummary,
    status_code=status.HTTP_201_CREATED,
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


@router.get("/{case_id}/requests", response_model=list[RequestItemSummary])
async def list_requests(case_id: str, session: DbSession) -> list[RequestItemSummary]:
    return await CaseService(session).list_requests(case_id)


@router.post(
    "/{case_id}/requests",
    response_model=RequestItemSummary,
    status_code=status.HTTP_201_CREATED,
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
