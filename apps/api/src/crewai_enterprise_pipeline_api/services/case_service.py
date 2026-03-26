from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from crewai_enterprise_pipeline_api.db.models import (
    CaseRecord,
    DocumentArtifactRecord,
    EvidenceNodeRecord,
    QaItemRecord,
    RequestItemRecord,
)
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


class CaseService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_cases(self) -> list[CaseSummary]:
        result = await self.session.execute(
            select(CaseRecord).order_by(CaseRecord.created_at.desc())
        )
        return [CaseSummary.model_validate(row) for row in result.scalars().all()]

    async def get_case(self, case_id: str) -> CaseDetail | None:
        record = await self._get_case_record(case_id)
        if record is None:
            return None
        return CaseDetail.model_validate(record)

    async def create_case(self, payload: CaseCreate) -> CaseDetail:
        record = CaseRecord(
            name=payload.name,
            target_name=payload.target_name,
            summary=payload.summary,
            motion_pack=payload.motion_pack.value,
            sector_pack=payload.sector_pack.value,
            country=payload.country,
        )
        self.session.add(record)
        await self.session.commit()
        return await self.get_case(record.id)  # type: ignore[return-value]

    async def list_documents(self, case_id: str) -> list[DocumentArtifactSummary]:
        case = await self._get_case_record(case_id)
        if case is None:
            return []
        return [DocumentArtifactSummary.model_validate(item) for item in case.documents]

    async def add_document(
        self,
        case_id: str,
        payload: DocumentArtifactCreate,
    ) -> DocumentArtifactSummary | None:
        if await self._get_case_record(case_id) is None:
            return None

        record = DocumentArtifactRecord(
            case_id=case_id,
            title=payload.title,
            source_kind=payload.source_kind.value,
            document_kind=payload.document_kind,
            mime_type=payload.mime_type,
            processing_status=payload.processing_status.value,
            storage_path=payload.storage_path,
        )
        self.session.add(record)
        await self.session.commit()
        await self.session.refresh(record)
        return DocumentArtifactSummary.model_validate(record)

    async def list_evidence(self, case_id: str) -> list[EvidenceItemSummary]:
        case = await self._get_case_record(case_id)
        if case is None:
            return []
        return [EvidenceItemSummary.model_validate(item) for item in case.evidence_items]

    async def add_evidence(
        self,
        case_id: str,
        payload: EvidenceItemCreate,
    ) -> EvidenceItemSummary | None:
        if await self._get_case_record(case_id) is None:
            return None

        record = EvidenceNodeRecord(
            case_id=case_id,
            artifact_id=payload.artifact_id,
            title=payload.title,
            evidence_kind=payload.evidence_kind.value,
            workstream_domain=payload.workstream_domain.value,
            citation=payload.citation,
            excerpt=payload.excerpt,
            confidence=payload.confidence,
        )
        self.session.add(record)
        await self.session.commit()
        await self.session.refresh(record)
        return EvidenceItemSummary.model_validate(record)

    async def list_requests(self, case_id: str) -> list[RequestItemSummary]:
        case = await self._get_case_record(case_id)
        if case is None:
            return []
        return [RequestItemSummary.model_validate(item) for item in case.request_items]

    async def add_request_item(
        self,
        case_id: str,
        payload: RequestItemCreate,
    ) -> RequestItemSummary | None:
        if await self._get_case_record(case_id) is None:
            return None

        record = RequestItemRecord(
            case_id=case_id,
            title=payload.title,
            detail=payload.detail,
            owner=payload.owner,
            status=payload.status.value,
        )
        self.session.add(record)
        await self.session.commit()
        await self.session.refresh(record)
        return RequestItemSummary.model_validate(record)

    async def list_qa_items(self, case_id: str) -> list[QaItemSummary]:
        case = await self._get_case_record(case_id)
        if case is None:
            return []
        return [QaItemSummary.model_validate(item) for item in case.qa_items]

    async def add_qa_item(
        self,
        case_id: str,
        payload: QaItemCreate,
    ) -> QaItemSummary | None:
        if await self._get_case_record(case_id) is None:
            return None

        record = QaItemRecord(
            case_id=case_id,
            question=payload.question,
            requested_by=payload.requested_by,
            response=payload.response,
            status=payload.status.value,
        )
        self.session.add(record)
        await self.session.commit()
        await self.session.refresh(record)
        return QaItemSummary.model_validate(record)

    async def _get_case_record(self, case_id: str) -> CaseRecord | None:
        result = await self.session.execute(
            select(CaseRecord)
            .where(CaseRecord.id == case_id)
            .options(
                selectinload(CaseRecord.documents),
                selectinload(CaseRecord.evidence_items),
                selectinload(CaseRecord.request_items),
                selectinload(CaseRecord.qa_items),
            )
        )
        return result.scalar_one_or_none()
