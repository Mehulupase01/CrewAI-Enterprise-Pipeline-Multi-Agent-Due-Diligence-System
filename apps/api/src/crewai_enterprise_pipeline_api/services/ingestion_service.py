from __future__ import annotations

from pathlib import Path

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from crewai_enterprise_pipeline_api.db.models import DocumentArtifactRecord, EvidenceNodeRecord
from crewai_enterprise_pipeline_api.domain.models import (
    ArtifactProcessingStatus,
    ArtifactSourceKind,
    DocumentArtifactSummary,
    DocumentIngestionResult,
    EvidenceKind,
    WorkstreamDomain,
)
from crewai_enterprise_pipeline_api.ingestion.parsers import DocumentParser, chunk_text
from crewai_enterprise_pipeline_api.services.case_service import CaseService
from crewai_enterprise_pipeline_api.storage.service import DocumentStorageService


class IngestionService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.case_service = CaseService(session)
        self.parser = DocumentParser()
        self.storage = DocumentStorageService()

    async def upload_document(
        self,
        *,
        case_id: str,
        file: UploadFile,
        document_kind: str,
        source_kind: ArtifactSourceKind,
        workstream_domain: WorkstreamDomain,
        title: str | None,
        evidence_kind: EvidenceKind,
    ) -> DocumentIngestionResult | None:
        case = await self.case_service._get_case_record(case_id)
        if case is None:
            return None

        content = await file.read()
        safe_name = Path(file.filename or "artifact.bin").name
        artifact = DocumentArtifactRecord(
            case_id=case_id,
            title=title or Path(safe_name).stem,
            original_filename=safe_name,
            source_kind=source_kind.value,
            document_kind=document_kind,
            mime_type=file.content_type,
            processing_status=ArtifactProcessingStatus.RECEIVED.value,
        )
        self.session.add(artifact)
        await self.session.flush()

        stored = self.storage.store_bytes(case_id, artifact.id, safe_name, content)
        parsed = self.parser.parse(safe_name, file.content_type, content)
        chunks = chunk_text(parsed.text)

        artifact.storage_path = stored.storage_path
        artifact.sha256_digest = stored.sha256_digest
        artifact.byte_size = stored.byte_size
        artifact.parser_name = parsed.parser_name
        artifact.processing_status = (
            ArtifactProcessingStatus.PARSED.value
            if chunks
            else ArtifactProcessingStatus.STAGED.value
        )

        evidence_records: list[EvidenceNodeRecord] = []
        for index, chunk in enumerate(chunks, start=1):
            evidence_records.append(
                EvidenceNodeRecord(
                    case_id=case_id,
                    artifact_id=artifact.id,
                    title=f"{artifact.title} / chunk {index}",
                    evidence_kind=evidence_kind.value,
                    workstream_domain=workstream_domain.value,
                    citation=f"{safe_name} :: chunk {index}",
                    excerpt=chunk,
                    confidence=0.75,
                )
            )

        self.session.add_all(evidence_records)
        await self.session.commit()
        await self.session.refresh(artifact)

        return DocumentIngestionResult(
            artifact=DocumentArtifactSummary.model_validate(artifact),
            evidence_items_created=len(evidence_records),
            extracted_character_count=parsed.extracted_character_count,
            parser_name=parsed.parser_name,
            storage_backend=stored.storage_backend,
        )
