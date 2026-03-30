from __future__ import annotations

from pathlib import Path

from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from crewai_enterprise_pipeline_api.db.models import (
    ChunkRecord,
    DocumentArtifactRecord,
    EvidenceNodeRecord,
)
from crewai_enterprise_pipeline_api.domain.models import (
    ArtifactProcessingStatus,
    ArtifactSourceKind,
    DocumentArtifactSummary,
    DocumentIngestionResult,
    EvidenceKind,
    WorkstreamDomain,
)
from crewai_enterprise_pipeline_api.ingestion.chunker import semantic_chunk
from crewai_enterprise_pipeline_api.ingestion.entity_extractor import extract_entities
from crewai_enterprise_pipeline_api.ingestion.parsers import DocumentParser
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

        # SHA256 dedup check — return existing artifact if same file already uploaded
        import hashlib

        digest = hashlib.sha256(content).hexdigest()
        existing = await self._find_by_digest(case_id, digest)
        if existing is not None:
            return DocumentIngestionResult(
                artifact=DocumentArtifactSummary.model_validate(existing),
                evidence_items_created=0,
                chunks_created=0,
                entities_extracted=0,
                extracted_character_count=0,
                parser_name=existing.parser_name or "dedup",
                storage_backend=self.storage.active_backend(),
            )

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

        # Semantic chunking — produces ChunkRecord instances
        sem_chunks = semantic_chunk(parsed.text)
        chunk_records: list[ChunkRecord] = []
        for sc in sem_chunks:
            chunk_records.append(
                ChunkRecord(
                    artifact_id=artifact.id,
                    chunk_index=sc.chunk_index,
                    section_title=sc.section_title,
                    text=sc.text,
                    page_number=sc.page_number,
                    char_start=sc.char_start,
                    char_end=sc.char_end,
                    has_embedding=False,
                )
            )

        # Evidence from chunks (legacy behaviour — one evidence per chunk)
        evidence_records: list[EvidenceNodeRecord] = []
        for index, sc in enumerate(sem_chunks, start=1):
            evidence_records.append(
                EvidenceNodeRecord(
                    case_id=case_id,
                    artifact_id=artifact.id,
                    title=f"{artifact.title} / chunk {index}",
                    evidence_kind=evidence_kind.value,
                    workstream_domain=workstream_domain.value,
                    citation=f"{safe_name} :: chunk {index}",
                    excerpt=sc.text,
                    confidence=0.75,
                )
            )

        # Entity extraction — produces additional structured evidence
        entity_items = extract_entities(
            parsed.text,
            document_kind=document_kind,
            artifact_id=artifact.id,
            citation_prefix=safe_name,
        )
        for ei in entity_items:
            evidence_records.append(
                EvidenceNodeRecord(
                    case_id=case_id,
                    artifact_id=artifact.id,
                    title=ei.title,
                    evidence_kind=ei.evidence_kind.value,
                    workstream_domain=ei.workstream_domain.value,
                    citation=ei.citation,
                    excerpt=ei.excerpt,
                    confidence=ei.confidence,
                )
            )

        artifact.storage_path = stored.storage_path
        artifact.sha256_digest = stored.sha256_digest
        artifact.byte_size = stored.byte_size
        artifact.parser_name = parsed.parser_name
        artifact.processing_status = (
            ArtifactProcessingStatus.PARSED.value
            if sem_chunks
            else ArtifactProcessingStatus.STAGED.value
        )

        self.session.add_all(chunk_records)
        self.session.add_all(evidence_records)
        await self.session.commit()
        await self.session.refresh(artifact)

        return DocumentIngestionResult(
            artifact=DocumentArtifactSummary.model_validate(artifact),
            evidence_items_created=len(evidence_records),
            chunks_created=len(chunk_records),
            entities_extracted=len(entity_items),
            extracted_character_count=parsed.extracted_character_count,
            parser_name=parsed.parser_name,
            storage_backend=stored.storage_backend,
        )

    async def _find_by_digest(
        self,
        case_id: str,
        digest: str,
    ) -> DocumentArtifactRecord | None:
        result = await self.session.execute(
            select(DocumentArtifactRecord).where(
                DocumentArtifactRecord.case_id == case_id,
                DocumentArtifactRecord.sha256_digest == digest,
            )
        )
        return result.scalar_one_or_none()
