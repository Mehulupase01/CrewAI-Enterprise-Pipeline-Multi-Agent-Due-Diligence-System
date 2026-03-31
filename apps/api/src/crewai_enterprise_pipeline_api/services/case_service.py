import hashlib

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from crewai_enterprise_pipeline_api.db.models import (
    CaseRecord,
    ChecklistItemRecord,
    ChunkRecord,
    DocumentArtifactRecord,
    EvidenceNodeRecord,
    IssueRegisterItemRecord,
    QaItemRecord,
    RequestItemRecord,
)
from crewai_enterprise_pipeline_api.domain.models import (
    ApprovalDecisionSummary,
    CaseCreate,
    CaseDetail,
    CaseSummary,
    CaseUpdate,
    ChecklistItemCreate,
    ChecklistItemSummary,
    ChecklistItemUpdate,
    ChunkSummary,
    DocumentArtifactCreate,
    DocumentArtifactSummary,
    EvidenceItemCreate,
    EvidenceItemSummary,
    EvidenceItemUpdate,
    IssueRegisterItemCreate,
    IssueRegisterItemSummary,
    IssueUpdate,
    QaItemCreate,
    QaItemSummary,
    QaItemUpdate,
    RequestItemCreate,
    RequestItemSummary,
    RequestItemUpdate,
)


class CaseService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_cases(
        self, *, skip: int = 0, limit: int = 100
    ) -> list[CaseSummary]:
        result = await self.session.execute(
            select(CaseRecord)
            .order_by(CaseRecord.created_at.desc())
            .offset(skip)
            .limit(limit)
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
            original_filename=payload.original_filename,
            source_kind=payload.source_kind.value,
            document_kind=payload.document_kind,
            mime_type=payload.mime_type,
            processing_status=payload.processing_status.value,
            storage_path=payload.storage_path,
            parser_name=payload.parser_name,
            sha256_digest=payload.sha256_digest,
            byte_size=payload.byte_size,
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

    async def list_issues(self, case_id: str) -> list[IssueRegisterItemSummary]:
        case = await self._get_case_record(case_id)
        if case is None:
            return []
        return [IssueRegisterItemSummary.model_validate(item) for item in case.issues]

    async def add_issue(
        self,
        case_id: str,
        payload: IssueRegisterItemCreate,
    ) -> IssueRegisterItemSummary | None:
        if await self._get_case_record(case_id) is None:
            return None

        fingerprint = hashlib.sha256(
            "|".join(
                [
                    case_id,
                    payload.title,
                    payload.summary,
                    payload.severity.value,
                    payload.workstream_domain.value,
                    payload.source_evidence_id or "",
                ]
            ).encode("utf-8")
        ).hexdigest()

        existing = await self.session.execute(
            select(IssueRegisterItemRecord).where(
                IssueRegisterItemRecord.fingerprint == fingerprint
            )
        )
        record = existing.scalar_one_or_none()
        if record is None:
            record = IssueRegisterItemRecord(
                case_id=case_id,
                source_evidence_id=payload.source_evidence_id,
                title=payload.title,
                summary=payload.summary,
                severity=payload.severity.value,
                status=payload.status.value,
                workstream_domain=payload.workstream_domain.value,
                business_impact=payload.business_impact,
                recommended_action=payload.recommended_action,
                confidence=payload.confidence,
                fingerprint=fingerprint,
            )
            self.session.add(record)
            await self.session.commit()
            await self.session.refresh(record)

        return IssueRegisterItemSummary.model_validate(record)

    async def list_checklist_items(self, case_id: str) -> list[ChecklistItemSummary]:
        case = await self._get_case_record(case_id)
        if case is None:
            return []
        return [
            ChecklistItemSummary.model_validate(item) for item in case.checklist_items
        ]

    async def add_checklist_item(
        self,
        case_id: str,
        payload: ChecklistItemCreate,
    ) -> ChecklistItemSummary | None:
        if await self._get_case_record(case_id) is None:
            return None

        record = ChecklistItemRecord(
            case_id=case_id,
            template_key=payload.template_key,
            title=payload.title,
            detail=payload.detail,
            workstream_domain=payload.workstream_domain.value,
            mandatory=payload.mandatory,
            evidence_required=payload.evidence_required,
            owner=payload.owner,
            note=payload.note,
            status=payload.status.value,
        )
        self.session.add(record)
        await self.session.commit()
        await self.session.refresh(record)
        return ChecklistItemSummary.model_validate(record)

    async def update_checklist_item(
        self,
        case_id: str,
        item_id: str,
        payload: ChecklistItemUpdate,
    ) -> ChecklistItemSummary | None:
        if await self._get_case_record(case_id) is None:
            return None

        result = await self.session.execute(
            select(ChecklistItemRecord).where(
                ChecklistItemRecord.id == item_id,
                ChecklistItemRecord.case_id == case_id,
            )
        )
        record = result.scalar_one_or_none()
        if record is None:
            return None

        if payload.status is not None:
            record.status = payload.status.value
        if payload.owner is not None:
            record.owner = payload.owner
        if payload.note is not None:
            record.note = payload.note

        await self.session.commit()
        await self.session.refresh(record)
        return ChecklistItemSummary.model_validate(record)

    async def update_case(
        self,
        case_id: str,
        payload: CaseUpdate,
    ) -> CaseDetail | None:
        case = await self._get_case_record(case_id)
        if case is None:
            return None
        for field, value in payload.model_dump(exclude_unset=True).items():
            if hasattr(value, "value"):
                value = value.value
            setattr(case, field, value)
        await self.session.commit()
        return await self.get_case(case_id)

    async def delete_case(self, case_id: str) -> bool:
        case = await self._get_case_record(case_id)
        if case is None:
            return False
        await self.session.delete(case)
        await self.session.commit()
        return True

    async def get_document(
        self, case_id: str, doc_id: str
    ) -> DocumentArtifactSummary | None:
        result = await self.session.execute(
            select(DocumentArtifactRecord).where(
                DocumentArtifactRecord.id == doc_id,
                DocumentArtifactRecord.case_id == case_id,
            )
        )
        record = result.scalar_one_or_none()
        if record is None:
            return None
        return DocumentArtifactSummary.model_validate(record)

    async def list_chunks(
        self,
        case_id: str,
        doc_id: str,
        *,
        skip: int = 0,
        limit: int = 200,
    ) -> list[ChunkSummary] | None:
        doc = await self.get_document(case_id, doc_id)
        if doc is None:
            return None
        result = await self.session.execute(
            select(ChunkRecord)
            .where(ChunkRecord.artifact_id == doc_id)
            .order_by(ChunkRecord.chunk_index)
            .offset(skip)
            .limit(limit)
        )
        return [ChunkSummary.model_validate(row) for row in result.scalars().all()]

    async def delete_document(self, case_id: str, doc_id: str) -> bool:
        result = await self.session.execute(
            select(DocumentArtifactRecord).where(
                DocumentArtifactRecord.id == doc_id,
                DocumentArtifactRecord.case_id == case_id,
            )
        )
        record = result.scalar_one_or_none()
        if record is None:
            return False
        await self.session.delete(record)
        await self.session.commit()
        return True

    async def get_evidence(
        self, case_id: str, evidence_id: str
    ) -> EvidenceItemSummary | None:
        result = await self.session.execute(
            select(EvidenceNodeRecord).where(
                EvidenceNodeRecord.id == evidence_id,
                EvidenceNodeRecord.case_id == case_id,
            )
        )
        record = result.scalar_one_or_none()
        if record is None:
            return None
        return EvidenceItemSummary.model_validate(record)

    async def update_evidence(
        self,
        case_id: str,
        evidence_id: str,
        payload: EvidenceItemUpdate,
    ) -> EvidenceItemSummary | None:
        result = await self.session.execute(
            select(EvidenceNodeRecord).where(
                EvidenceNodeRecord.id == evidence_id,
                EvidenceNodeRecord.case_id == case_id,
            )
        )
        record = result.scalar_one_or_none()
        if record is None:
            return None
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(record, field, value)
        await self.session.commit()
        await self.session.refresh(record)
        return EvidenceItemSummary.model_validate(record)

    async def get_issue(
        self, case_id: str, issue_id: str
    ) -> IssueRegisterItemSummary | None:
        result = await self.session.execute(
            select(IssueRegisterItemRecord).where(
                IssueRegisterItemRecord.id == issue_id,
                IssueRegisterItemRecord.case_id == case_id,
            )
        )
        record = result.scalar_one_or_none()
        if record is None:
            return None
        return IssueRegisterItemSummary.model_validate(record)

    async def update_issue(
        self,
        case_id: str,
        issue_id: str,
        payload: IssueUpdate,
    ) -> IssueRegisterItemSummary | None:
        result = await self.session.execute(
            select(IssueRegisterItemRecord).where(
                IssueRegisterItemRecord.id == issue_id,
                IssueRegisterItemRecord.case_id == case_id,
            )
        )
        record = result.scalar_one_or_none()
        if record is None:
            return None
        for field, value in payload.model_dump(exclude_unset=True).items():
            if hasattr(value, "value"):
                value = value.value
            setattr(record, field, value)
        await self.session.commit()
        await self.session.refresh(record)
        return IssueRegisterItemSummary.model_validate(record)

    async def delete_issue(self, case_id: str, issue_id: str) -> bool:
        result = await self.session.execute(
            select(IssueRegisterItemRecord).where(
                IssueRegisterItemRecord.id == issue_id,
                IssueRegisterItemRecord.case_id == case_id,
            )
        )
        record = result.scalar_one_or_none()
        if record is None:
            return False
        await self.session.delete(record)
        await self.session.commit()
        return True

    async def update_request_item(
        self,
        case_id: str,
        item_id: str,
        payload: RequestItemUpdate,
    ) -> RequestItemSummary | None:
        result = await self.session.execute(
            select(RequestItemRecord).where(
                RequestItemRecord.id == item_id,
                RequestItemRecord.case_id == case_id,
            )
        )
        record = result.scalar_one_or_none()
        if record is None:
            return None
        for field, value in payload.model_dump(exclude_unset=True).items():
            if hasattr(value, "value"):
                value = value.value
            setattr(record, field, value)
        await self.session.commit()
        await self.session.refresh(record)
        return RequestItemSummary.model_validate(record)

    async def update_qa_item(
        self,
        case_id: str,
        item_id: str,
        payload: QaItemUpdate,
    ) -> QaItemSummary | None:
        result = await self.session.execute(
            select(QaItemRecord).where(
                QaItemRecord.id == item_id,
                QaItemRecord.case_id == case_id,
            )
        )
        record = result.scalar_one_or_none()
        if record is None:
            return None
        for field, value in payload.model_dump(exclude_unset=True).items():
            if hasattr(value, "value"):
                value = value.value
            setattr(record, field, value)
        await self.session.commit()
        await self.session.refresh(record)
        return QaItemSummary.model_validate(record)

    async def list_approvals(self, case_id: str) -> list[ApprovalDecisionSummary]:
        case = await self._get_case_record(case_id)
        if case is None:
            return []
        return [ApprovalDecisionSummary.model_validate(item) for item in case.approvals]

    async def _get_case_record(self, case_id: str) -> CaseRecord | None:
        result = await self.session.execute(
            select(CaseRecord)
            .where(CaseRecord.id == case_id)
            .options(
                selectinload(CaseRecord.approvals),
                selectinload(CaseRecord.checklist_items),
                selectinload(CaseRecord.documents).selectinload(DocumentArtifactRecord.chunks),
                selectinload(CaseRecord.evidence_items),
                selectinload(CaseRecord.issues),
                selectinload(CaseRecord.request_items),
                selectinload(CaseRecord.qa_items),
            )
        )
        return result.scalar_one_or_none()
