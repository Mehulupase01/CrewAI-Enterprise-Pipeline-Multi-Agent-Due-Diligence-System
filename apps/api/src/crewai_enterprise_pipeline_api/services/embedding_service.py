"""Embedding service for vector-encoding document chunks.

Supports three providers:
  - ``none``: No-op — embeddings are skipped (default for dev/test).
  - ``openai``: Uses the OpenAI Embeddings API via ``httpx``.
  - ``local``: Uses ``sentence-transformers`` (optional dependency).

Embeddings are stored as raw ``float32`` bytes in ``ChunkRecord.embedding``
and can be cast to ``vector(N)`` by PostgreSQL / pgvector at query time.
"""

from __future__ import annotations

import logging
import struct

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from crewai_enterprise_pipeline_api.core.settings import get_settings
from crewai_enterprise_pipeline_api.db.models import ChunkRecord

logger = logging.getLogger(__name__)


def _floats_to_bytes(vec: list[float]) -> bytes:
    """Pack a float list into raw little-endian float32 bytes."""
    return struct.pack(f"<{len(vec)}f", *vec)


def _bytes_to_floats(raw: bytes) -> list[float]:
    """Unpack raw little-endian float32 bytes into a float list."""
    count = len(raw) // 4
    return list(struct.unpack(f"<{count}f", raw))


class EmbeddingService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self._settings = get_settings()

    @property
    def provider(self) -> str:
        return self._settings.embedding_provider

    @property
    def dimensions(self) -> int:
        return self._settings.embedding_dimensions

    async def embed_chunks(self, artifact_id: str) -> int:
        """Generate embeddings for all un-embedded chunks of an artifact.

        Returns the number of chunks newly embedded.
        """
        if self.provider == "none":
            logger.debug("Embedding provider is 'none'; skipping embedding generation")
            return 0

        result = await self.session.execute(
            select(ChunkRecord).where(
                ChunkRecord.artifact_id == artifact_id,
                ChunkRecord.has_embedding.is_(False),
            )
        )
        chunks = list(result.scalars().all())
        if not chunks:
            return 0

        texts = [c.text for c in chunks]
        vectors = await self._generate_vectors(texts)

        for chunk, vec in zip(chunks, vectors, strict=True):
            chunk.embedding = _floats_to_bytes(vec)
            chunk.has_embedding = True

        await self.session.commit()
        logger.info("Embedded %d chunks for artifact %s", len(chunks), artifact_id)
        return len(chunks)

    async def embed_text(self, text: str) -> list[float] | None:
        """Embed a single text string (e.g. a search query).

        Returns ``None`` if the provider is ``'none'``.
        """
        if self.provider == "none":
            return None
        vectors = await self._generate_vectors([text])
        return vectors[0]

    async def _generate_vectors(self, texts: list[str]) -> list[list[float]]:
        """Dispatch to the configured embedding provider."""
        if self.provider == "openai":
            return await self._embed_openai(texts)
        if self.provider == "local":
            return self._embed_local(texts)
        msg = f"Unknown embedding provider: {self.provider}"
        raise ValueError(msg)

    async def _embed_openai(self, texts: list[str]) -> list[list[float]]:
        """Call the OpenAI Embeddings API."""
        import httpx

        api_key = self._settings.embedding_api_key
        if not api_key:
            msg = "EMBEDDING_API_KEY is required when embedding_provider is 'openai'"
            raise ValueError(msg)

        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.openai.com/v1/embeddings",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self._settings.embedding_model,
                    "input": texts,
                    "dimensions": self.dimensions,
                },
                timeout=60.0,
            )
            response.raise_for_status()
            data = response.json()

        # Sort by index to maintain order
        embeddings = sorted(data["data"], key=lambda x: x["index"])
        return [e["embedding"] for e in embeddings]

    def _embed_local(self, texts: list[str]) -> list[list[float]]:
        """Use sentence-transformers for local embedding."""
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            msg = (
                "sentence-transformers is required for local embeddings. "
                "Install with: pip install sentence-transformers"
            )
            raise ImportError(msg) from exc

        model = SentenceTransformer(self._settings.embedding_model)
        vectors = model.encode(texts, show_progress_bar=False)
        return [v.tolist() for v in vectors]
