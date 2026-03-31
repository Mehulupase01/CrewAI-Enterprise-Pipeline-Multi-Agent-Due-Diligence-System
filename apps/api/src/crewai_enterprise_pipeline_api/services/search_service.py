"""Hybrid search and evidence conflict detection.

Search strategy:
  1. **Keyword (BM25-like):** SQLite uses ``LIKE``; PostgreSQL uses
     ``to_tsvector / plainto_tsquery`` with ``ts_rank``.
  2. **Cosine similarity:** Only available when chunks have embeddings.
  3. **Hybrid:** ``final_score = 0.4 * bm25_norm + 0.6 * cosine_norm``
     when both scores are available; otherwise falls back to whichever
     is available.

Conflict detection:
  - Compares embedding similarity between evidence pairs within a case.
  - ``similarity > 0.98`` → DUPLICATE
  - ``similarity > 0.92`` with different extracted values → CONTRADICTORY
"""

from __future__ import annotations

import logging
import math

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from crewai_enterprise_pipeline_api.db.models import (
    ChunkRecord,
    DocumentArtifactRecord,
    EvidenceNodeRecord,
)
from crewai_enterprise_pipeline_api.domain.models import (
    ConflictType,
    EvidenceConflict,
    EvidenceSearchResponse,
    EvidenceSearchResult,
    SearchRequest,
    WorkstreamDomain,
)
from crewai_enterprise_pipeline_api.services.embedding_service import (
    EmbeddingService,
    _bytes_to_floats,
)

logger = logging.getLogger(__name__)


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Pure-Python cosine similarity between two vectors."""
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


class SearchService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.embedding_service = EmbeddingService(session)

    async def hybrid_search(
        self,
        case_id: str,
        request: SearchRequest,
    ) -> EvidenceSearchResponse:
        """Run hybrid keyword + semantic search across case chunks."""
        # Get all chunks for this case
        chunks = await self._get_case_chunks(case_id, request.workstream_domain)
        if not chunks:
            return EvidenceSearchResponse(results=[], total=0)

        # Keyword scoring
        keyword_scores = self._keyword_score(chunks, request.query)

        # Semantic scoring (if embeddings available)
        query_vec = await self.embedding_service.embed_text(request.query)
        cosine_scores = self._cosine_score(chunks, query_vec) if query_vec else {}

        # Combine scores
        scored = self._combine_scores(chunks, keyword_scores, cosine_scores)

        # Sort by score descending, take top_k
        scored.sort(key=lambda x: x[1], reverse=True)
        top = scored[: request.top_k]

        results = [
            EvidenceSearchResult(
                chunk_id=chunk.id,
                artifact_id=chunk.artifact_id,
                text=chunk.text,
                score=round(score, 4),
                section_title=chunk.section_title,
                page_number=chunk.page_number,
            )
            for chunk, score in top
            if score > 0
        ]

        return EvidenceSearchResponse(results=results, total=len(results))

    async def detect_conflicts(
        self,
        case_id: str,
    ) -> list[EvidenceConflict]:
        """Detect duplicate or contradictory evidence within a case.

        Compares embeddings of evidence excerpts. When embeddings are not
        available, falls back to simple text overlap detection.
        """
        result = await self.session.execute(
            select(EvidenceNodeRecord).where(EvidenceNodeRecord.case_id == case_id)
        )
        evidence_items = list(result.scalars().all())
        if len(evidence_items) < 2:
            return []

        # Try to find chunks with embeddings for each evidence item
        embedded_chunks = await self._get_embedded_chunks_for_case(case_id)
        chunk_by_text: dict[str, list[float]] = {}
        for chunk in embedded_chunks:
            if chunk.embedding:
                chunk_by_text[chunk.text.strip()] = _bytes_to_floats(chunk.embedding)

        conflicts: list[EvidenceConflict] = []

        for i, ev_a in enumerate(evidence_items):
            for ev_b in evidence_items[i + 1 :]:
                sim = self._evidence_similarity(ev_a, ev_b, chunk_by_text)
                if sim is None:
                    continue

                if sim > 0.98:
                    conflicts.append(
                        EvidenceConflict(
                            evidence_a_id=ev_a.id,
                            evidence_b_id=ev_b.id,
                            similarity=round(sim, 4),
                            conflict_type=ConflictType.DUPLICATE,
                            explanation=(
                                f"Evidence items are near-identical "
                                f"(similarity {sim:.2%}): "
                                f"'{ev_a.title}' and '{ev_b.title}'"
                            ),
                        )
                    )
                elif sim > 0.92 and ev_a.excerpt.strip() != ev_b.excerpt.strip():
                    conflicts.append(
                        EvidenceConflict(
                            evidence_a_id=ev_a.id,
                            evidence_b_id=ev_b.id,
                            similarity=round(sim, 4),
                            conflict_type=ConflictType.CONTRADICTORY,
                            explanation=(
                                f"Evidence items are highly similar "
                                f"(similarity {sim:.2%}) but contain "
                                f"different values: '{ev_a.title}' vs '{ev_b.title}'"
                            ),
                        )
                    )

        return conflicts

    async def _get_case_chunks(
        self,
        case_id: str,
        workstream_domain: WorkstreamDomain | None = None,
    ) -> list[ChunkRecord]:
        """Get all chunks for a case, optionally filtered by workstream."""
        stmt = (
            select(ChunkRecord)
            .join(DocumentArtifactRecord)
            .where(DocumentArtifactRecord.case_id == case_id)
        )

        if workstream_domain is not None:
            # Filter by evidence items linked to this workstream
            subquery = (
                select(DocumentArtifactRecord.id)
                .join(
                    EvidenceNodeRecord, EvidenceNodeRecord.artifact_id == DocumentArtifactRecord.id
                )
                .where(
                    DocumentArtifactRecord.case_id == case_id,
                    EvidenceNodeRecord.workstream_domain == workstream_domain.value,
                )
            )
            stmt = stmt.where(DocumentArtifactRecord.id.in_(subquery))

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    def _keyword_score(
        self,
        chunks: list[ChunkRecord],
        query: str,
    ) -> dict[str, float]:
        """Simple keyword matching score (0-1).

        Counts how many query terms appear in each chunk text, normalized
        by total query terms. This serves as a BM25 approximation for
        SQLite; PostgreSQL would use ``ts_rank`` via raw SQL.
        """
        terms = query.lower().split()
        if not terms:
            return {}

        scores: dict[str, float] = {}
        for chunk in chunks:
            lower_text = chunk.text.lower()
            matches = sum(1 for t in terms if t in lower_text)
            scores[chunk.id] = matches / len(terms)

        return scores

    def _cosine_score(
        self,
        chunks: list[ChunkRecord],
        query_vec: list[float],
    ) -> dict[str, float]:
        """Compute cosine similarity between query vector and chunk embeddings."""
        scores: dict[str, float] = {}
        for chunk in chunks:
            if chunk.embedding:
                chunk_vec = _bytes_to_floats(chunk.embedding)
                sim = _cosine_similarity(query_vec, chunk_vec)
                scores[chunk.id] = max(0.0, sim)  # clamp to [0, 1]
        return scores

    def _combine_scores(
        self,
        chunks: list[ChunkRecord],
        keyword_scores: dict[str, float],
        cosine_scores: dict[str, float],
    ) -> list[tuple[ChunkRecord, float]]:
        """Combine keyword and cosine scores with 0.4/0.6 weighting."""
        # Normalize keyword scores
        kw_max = max(keyword_scores.values()) if keyword_scores else 0
        cos_max = max(cosine_scores.values()) if cosine_scores else 0

        results: list[tuple[ChunkRecord, float]] = []
        for chunk in chunks:
            kw = keyword_scores.get(chunk.id, 0.0)
            cos = cosine_scores.get(chunk.id, 0.0)

            kw_norm = kw / kw_max if kw_max > 0 else 0.0
            cos_norm = cos / cos_max if cos_max > 0 else 0.0

            if cosine_scores and keyword_scores:
                score = 0.4 * kw_norm + 0.6 * cos_norm
            elif cosine_scores:
                score = cos_norm
            else:
                score = kw_norm

            results.append((chunk, score))

        return results

    async def _get_embedded_chunks_for_case(
        self,
        case_id: str,
    ) -> list[ChunkRecord]:
        """Get chunks that have embeddings for a case."""
        result = await self.session.execute(
            select(ChunkRecord)
            .join(DocumentArtifactRecord)
            .where(
                DocumentArtifactRecord.case_id == case_id,
                ChunkRecord.has_embedding.is_(True),
            )
        )
        return list(result.scalars().all())

    def _evidence_similarity(
        self,
        ev_a: EvidenceNodeRecord,
        ev_b: EvidenceNodeRecord,
        chunk_embeddings: dict[str, list[float]],
    ) -> float | None:
        """Compute similarity between two evidence items.

        Uses embedding cosine similarity if available, otherwise falls back
        to simple text overlap ratio.
        """
        # Try embedding-based similarity
        vec_a = chunk_embeddings.get(ev_a.excerpt.strip())
        vec_b = chunk_embeddings.get(ev_b.excerpt.strip())
        if vec_a and vec_b:
            return _cosine_similarity(vec_a, vec_b)

        # Fallback: simple word overlap (Jaccard-like)
        words_a = set(ev_a.excerpt.lower().split())
        words_b = set(ev_b.excerpt.lower().split())
        if not words_a or not words_b:
            return None
        intersection = words_a & words_b
        union = words_a | words_b
        return len(intersection) / len(union) if union else None
