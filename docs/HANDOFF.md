# Session Handoff

> This file is updated during active work so that if a session dies mid-phase,
> the next session can resume exactly where we left off.
>
> READ THIS FIRST if you are an AI agent resuming work on this project.

## Current State

**Active phase:** None (Phase 4 complete, ready to start Phase 5)
**Phase status:** Complete
**Last session:** 2026-03-30

## What to do next

1. Read `CLAUDE.md` for project context and commands
2. Read `docs/PROGRESS.md` for completion history
3. Read `docs/DECISIONS.md` for design rationale
4. Start Phase 5: Evidence Intelligence + pgvector Hybrid Search (see `docs/MASTERPLAN.pdf`)

## Files modified this phase (checkpoint)

- `apps/api/src/.../db/models.py` -- added ChunkRecord ORM model with artifact relationship
- `apps/api/src/.../domain/models.py` -- added ChunkSummary schema; added chunks_created/entities_extracted to DocumentIngestionResult
- `apps/api/src/.../ingestion/chunker.py` -- NEW: semantic chunking engine (heading > paragraph > sentence splitting)
- `apps/api/src/.../ingestion/entity_extractor.py` -- NEW: rule-based entity extractor (financial, legal, regulatory, India identifiers)
- `apps/api/src/.../ingestion/parsers.py` -- upgraded PDF (table extraction), DOCX (heading structure + tables), XLSX (markdown tables, all sheets)
- `apps/api/src/.../services/ingestion_service.py` -- wired chunker + entity extractor; SHA256 dedup check
- `apps/api/src/.../services/case_service.py` -- added list_chunks() method
- `apps/api/src/.../api/routes/cases.py` -- added GET /documents/{doc_id}/chunks endpoint
- `apps/api/src/.../storage/service.py` -- added active_backend() helper
- `apps/api/tests/test_phase4_document_intelligence.py` -- NEW: 10 tests

## Files remaining this phase

_None -- Phase 4 is complete._

## Tests run

- ruff: clean
- pytest: 60/60 pass (50 existing + 10 new)
- eval suites: 11/11 pass (5 suites, all 100%)
- npm lint: clean
- npm typecheck: clean

## Blockers

_None._

## Notes for next session

- Phase 5 spec is in docs/MASTERPLAN.pdf (pages 21-22)
- Phase 5 adds pgvector embeddings, hybrid search, evidence conflict detection
- ChunkRecord is ready for the embedding vector column (Phase 5 migration 002)
- Entity extractor covers: revenue, EBITDA, PAT, net debt, auditor, audit opinion, parties, dates, governing law, CIN, GSTIN, registration numbers
- Document dedup uses SHA256 — uploading same file twice returns existing artifact
