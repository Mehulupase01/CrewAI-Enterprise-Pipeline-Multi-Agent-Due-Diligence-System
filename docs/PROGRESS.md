# Master Plan Execution Progress

> This file is the single source of truth for what has been implemented.
> Any AI agent resuming work should read this file + CLAUDE.md first.

## Status: Phase 6 Complete

**Last updated:** 2026-03-31
**Completed phases:** Phase 0, Phase 1, Phase 2, Phase 3, Phase 4, Phase 5, Phase 6
**Next phase:** Phase 7 -- CrewAI Multi-Agent Orchestration
**Blocking issues:** None

---

## Phase Completion Log

### Phase 0: Setup & Planning (2026-03-29)

**What was done:**
- Migrated from OpenAI Codex to Claude Code
- Created CLAUDE.md with accurate project assessment
- Created .claude/ directory (settings.json, commands, rules, agents)
- Audited entire codebase -- identified all broken/incomplete items
- Generated 54-page Master Plan PDF (docs/MASTERPLAN.pdf)
- PDF generator script: generate_masterplan_pdf.py

**Key findings from audit:**
- CrewAI 1.12.2 declared but NEVER imported (zero AI in the system)
- pdfplumber, openpyxl imported but missing from pyproject.toml
- No error handling in workflow_service.execute_run()
- Frontend is 100% read-only (zero POST/PATCH/DELETE)
- Alembic installed but no migrations; Redis declared but unused
- Issue heuristics use naive substring matching (false positives)
- Health endpoint has hardcoded values
- Approval has no manual decision override

**Files created this session:**
- CLAUDE.md (project context)
- .claude/settings.json (permissions)
- .claude/commands/review.md (code review slash command)
- .claude/commands/test.md (test slash command)
- .claude/rules/code-style.md (Python + TypeScript conventions)
- .claude/rules/testing.md (two-layer test strategy)
- .claude/agents/code-reviewer.md (code review agent)
- generate_masterplan_pdf.py (PDF generator)
- docs/MASTERPLAN.pdf (54-page master plan)
- docs/PROGRESS.md (this file)

**Tests:** All 24 existing pytest tests pass. All 11 evaluation scenarios pass. No regressions.

---

### Phase 1: Critical Fixes & Dependency Repair (2026-03-30)

**What was done:**
- Added pdfplumber and openpyxl to pyproject.toml (fixing import-without-dependency bug)
- Added try/except error handling to workflow_service.execute_run() -- runs now get FAILED status + trace event on error instead of hanging in RUNNING forever
- Added logger.warning when storage service falls back from S3 to local (was silent)
- Added REJECTED and CONDITIONALLY_APPROVED to ApprovalDecisionKind enum
- Added optional `decision` field to ApprovalDecisionCreate for reviewer override
- Wired decision override into approval_service.review_case()
- Wrapped all document parsers (PDF, DOCX, XLSX, CSV, JSON) in try/except with logger.warning -- corrupt files return empty string instead of crashing
- Replaced naive substring matching in issue_service with word-boundary regex (`re.search(r'\b' + re.escape(pattern) + r'\b', ...)`)
- Added configurable settings: product_name, current_phase, country, enabled_motion_packs, enabled_sector_packs
- Health and overview endpoints now read from Settings instead of hardcoded values
- Added 5 new pytest tests covering all Phase 1 changes

**Files created:**
- apps/api/tests/test_phase1_fixes.py -- 5 new test cases

**Files modified:**
- apps/api/pyproject.toml -- added pdfplumber>=0.11, openpyxl>=3.1
- apps/api/src/.../domain/models.py -- extended ApprovalDecisionKind, added decision to ApprovalDecisionCreate
- apps/api/src/.../core/settings.py -- added 5 new config fields
- apps/api/src/.../api/routes/health.py -- reads from config instead of hardcoded
- apps/api/src/.../services/workflow_service.py -- error handling with FAILED status
- apps/api/src/.../services/issue_service.py -- word-boundary regex
- apps/api/src/.../services/approval_service.py -- decision override
- apps/api/src/.../ingestion/parsers.py -- try/except on all parsers
- apps/api/src/.../storage/service.py -- fallback warning log

**Decisions made:**
- AD-008: Word-boundary regex preserves all existing eval scenarios (no false-negative regression)
- AD-009: Reviewer decision override is optional; auto-computed logic remains the default

**Blockers encountered:**
- None

**Test results:**
- pytest: 29/29 pass (24 existing + 5 new)
- eval suites: 11/11 pass (all 5 suites at 100%)
- ruff: clean
- npm lint: clean
- npm typecheck: clean

**Notes for next phase:**
- Phase 2 adds PATCH/DELETE/individual GET/pagination/filtering/download endpoint
- New ApprovalDecisionKind values available but not yet used in evaluation scenarios
- Word-boundary regex is stricter but all existing scenarios still pass

---

### Phase 2: API Completeness (2026-03-30)

**What was done:**
- Added 5 update Pydantic schemas: CaseUpdate, IssueUpdate, RequestItemUpdate, QaItemUpdate, EvidenceItemUpdate
- Added full CRUD service methods to case_service: update_case, delete_case, get_document, delete_document, get_evidence, update_evidence, get_issue, update_issue, delete_issue, update_request_item, update_qa_item
- Added pagination (skip/limit) to list_cases endpoint
- Added PATCH endpoints: cases, issues, evidence, requests, Q&A
- Added DELETE endpoints: cases (cascade), documents, issues
- Added individual GET endpoints: documents/{id}, evidence/{id}, issues/{id}
- Added download endpoint: export-packages/{id}/download (streams ZIP)
- Added retrieve_bytes() to storage service for file download from local/S3
- Added 12 new pytest tests covering all new endpoints

**Files created:**
- apps/api/tests/test_phase2_api_completeness.py -- 12 new test cases

**Files modified:**
- apps/api/src/.../domain/models.py -- 5 new update schemas
- apps/api/src/.../services/case_service.py -- 11 new service methods, pagination on list_cases
- apps/api/src/.../api/routes/cases.py -- 11 new endpoints (5 PATCH, 3 DELETE, 3 GET)
- apps/api/src/.../storage/service.py -- retrieve_bytes() method

**Decisions made:**
- AD-010: Pagination on list_cases only for now; other lists typically scoped by case_id
- AD-011: DELETE /cases cascade-deletes all children (leveraging existing CaseRecord cascade)
- AD-012: Download endpoint returns full file content via Response (not streaming) -- sufficient for current ZIP sizes

**Blockers encountered:**
- None

**Test results:**
- pytest: 41/41 pass (29 existing + 12 new)
- eval suites: 11/11 pass (all 5 suites at 100%)
- ruff: clean
- npm lint: clean
- npm typecheck: clean

**Notes for next phase:**
- Phase 3 adds Alembic, arq worker, Redis wiring, SSE endpoint
- API surface is now complete for frontend mutations (Phase 6)

---

### Phase 3: Infrastructure Wiring — Alembic + arq + Redis (2026-03-30)

**What was done:**
- Created Alembic config (alembic.ini, env.py, script.py.mako) with async migration support
- Created initial Alembic migration (001_initial_schema.py) capturing all 14 ORM tables
- Created arq worker module (worker.py) with run_workflow_job task, startup/shutdown hooks
- Added WorkflowRunEnqueueResult schema for async dispatch responses
- Modified main.py lifespan to optionally connect Redis pool (background_mode setting)
- Modified POST /runs to enqueue via arq when Redis is available, fall back to sync otherwise
- Added SSE stream endpoint (GET /runs/{id}/stream) for real-time run progress
- Added settings: worker_concurrency (4), max_upload_mb (50), background_mode (false)
- Relaxed redis dependency to >=5.0,<6 for arq 0.27 compatibility
- Created dev-worker.ps1 launcher script
- Added 9 new pytest tests covering all Phase 3 features

**Files created:**
- apps/api/alembic.ini -- Alembic config
- apps/api/alembic/env.py -- async migration environment
- apps/api/alembic/script.py.mako -- migration template
- apps/api/alembic/versions/001_initial_schema.py -- initial migration (14 tables)
- apps/api/src/.../worker.py -- arq WorkerSettings + job function
- apps/api/tests/test_phase3_infrastructure.py -- 9 new test cases
- scripts/dev-worker.ps1 -- arq worker launcher

**Files modified:**
- apps/api/pyproject.toml -- added arq>=0.26, relaxed redis to >=5.0,<6
- apps/api/src/.../core/settings.py -- 3 new settings, updated current_phase
- apps/api/src/.../main.py -- Redis pool wiring in lifespan
- apps/api/src/.../domain/models.py -- WorkflowRunEnqueueResult schema
- apps/api/src/.../services/workflow_service.py -- enqueue_run() method
- apps/api/src/.../api/routes/cases.py -- async/sync POST /runs, SSE stream endpoint
- apps/api/tests/test_phase1_fixes.py -- relaxed current_phase assertion

**Decisions made:**
- AD-013: background_mode defaults to false; sync execution preserved for dev/test
- AD-014: arq 0.27 requires redis<6, so redis pin relaxed from ==7.4.0 to >=5.0,<6
- AD-015: SSE stream polls at 1-second intervals; closes on terminal run status

**Blockers encountered:**
- None

**Test results:**
- pytest: 50/50 pass (41 existing + 9 new)
- eval suites: 11/11 pass (all 5 suites at 100%)
- ruff: clean
- npm lint: clean
- npm typecheck: clean

**Notes for next phase:**
- Phase 4 wires the Next.js frontend to POST/PATCH/DELETE endpoints
- SSE endpoint available for live run streaming in the UI
- Worker is standalone: `arq crewai_enterprise_pipeline_api.worker.WorkerSettings`

---

### Phase 4: Document Intelligence (2026-03-30)

**What was done:**
- Created ChunkRecord ORM model linked to DocumentArtifactRecord (cascade delete)
- Created semantic chunking engine (ingestion/chunker.py): splits by heading > paragraph > sentence with char offsets and page detection
- Created rule-based entity extractor (ingestion/entity_extractor.py): financial (revenue, EBITDA, PAT, debt, auditor, opinion), legal (parties, dates, governing law), regulatory (reg numbers, validity), India identifiers (CIN, GSTIN)
- Upgraded PDF parser to extract tables as markdown via pdfplumber
- Upgraded DOCX parser to preserve heading structure (markdown #) and extract tables
- Upgraded XLSX parser to render all sheets as markdown tables (up to 8 sheets, 200 rows)
- Wired semantic chunker and entity extractor into ingestion service
- Added SHA256 document dedup — uploading same file returns existing artifact
- Added GET /documents/{doc_id}/chunks endpoint with pagination
- Added ChunkSummary schema; extended DocumentIngestionResult with chunks_created and entities_extracted
- Added 10 new pytest tests

**Files created:**
- apps/api/src/.../ingestion/chunker.py -- semantic chunking engine
- apps/api/src/.../ingestion/entity_extractor.py -- rule-based entity extractor
- apps/api/tests/test_phase4_document_intelligence.py -- 10 test cases

**Files modified:**
- apps/api/src/.../db/models.py -- ChunkRecord ORM model + relationship on DocumentArtifactRecord
- apps/api/src/.../domain/models.py -- ChunkSummary, extended DocumentIngestionResult
- apps/api/src/.../ingestion/parsers.py -- PDF table extraction, DOCX headings+tables, XLSX markdown tables
- apps/api/src/.../services/ingestion_service.py -- chunker + extractor wiring, SHA256 dedup
- apps/api/src/.../services/case_service.py -- list_chunks() method
- apps/api/src/.../api/routes/cases.py -- GET /documents/{doc_id}/chunks endpoint
- apps/api/src/.../storage/service.py -- active_backend() helper

**Decisions made:**
- AD-016: Semantic chunking uses heading-first splitting (heading > paragraph > sentence) with 1200-char default
- AD-017: Entity extraction is rule-based (regex), not LLM-dependent — deterministic and testable
- AD-018: Document dedup by SHA256 — same content returns existing artifact with zero new evidence

**Blockers encountered:**
- None

**Test results:**
- pytest: 60/60 pass (50 existing + 10 new)
- eval suites: 11/11 pass (all 5 suites at 100%)
- ruff: clean
- npm lint: clean
- npm typecheck: clean

**Notes for next phase:**
- Phase 5 adds pgvector embeddings to ChunkRecord + hybrid search
- ChunkRecord.has_embedding is false for all rows — Phase 5 migration will add vector column
- Entity extractor covers India-specific patterns (CIN, GSTIN) regardless of document kind

---

### Phase 5: Evidence Intelligence + pgvector Hybrid Search (2026-03-30)

**What was done:**
- Added pgvector>=0.3 dependency and sentence-transformers as optional
- Created Alembic migration 002: pgvector extension, embedding vector(1536) column, HNSW + GIN indexes
- Added embedding column (LargeBinary, nullable) to ChunkRecord ORM
- Added embedding settings: embedding_provider (none/openai/local), embedding_model, embedding_api_key, embedding_dimensions
- Created EmbeddingService: batch embed chunks via configurable provider (none/openai/local), float32 byte packing
- Created SearchService: hybrid keyword + cosine search with 0.4/0.6 weighting, evidence conflict detection (duplicate >0.98, contradictory >0.92)
- Added Pydantic schemas: SearchRequest, EvidenceSearchResult, EvidenceSearchResponse, ConflictType, EvidenceConflict
- Added POST /cases/{id}/search endpoint (hybrid search)
- Added GET /cases/{id}/evidence/conflicts endpoint (auto-detect duplicates/contradictions)
- Added 11 new pytest tests

**Files created:**
- apps/api/alembic/versions/002_pgvector_embedding.py -- pgvector migration
- apps/api/src/.../services/embedding_service.py -- embedding generation service
- apps/api/src/.../services/search_service.py -- hybrid search + conflict detection
- apps/api/tests/test_phase5_evidence_intelligence.py -- 11 test cases

**Files modified:**
- apps/api/pyproject.toml -- added pgvector>=0.3, sentence-transformers optional
- apps/api/src/.../core/settings.py -- 4 new embedding settings, updated current_phase
- apps/api/src/.../db/models.py -- ChunkRecord.embedding column (LargeBinary)
- apps/api/src/.../domain/models.py -- 5 new schemas (SearchRequest, EvidenceSearchResult, EvidenceSearchResponse, ConflictType, EvidenceConflict)
- apps/api/src/.../api/routes/cases.py -- 2 new endpoints (search, conflicts)

**Decisions made:**
- AD-019: Embeddings stored as raw float32 bytes in LargeBinary (SQLite-compatible); cast to vector(1536) by pgvector at query time
- AD-020: Embedding provider defaults to "none" — search falls back to keyword-only; tests work without API keys
- AD-021: Conflict detection uses embedding cosine similarity when available, Jaccard word overlap as fallback

**Test results:**
- pytest: 71/71 pass (60 existing + 11 new)
- eval suites: 11/11 pass (all 5 suites at 100%)
- ruff: clean
- npm lint: clean
- npm typecheck: clean

**Notes for next phase:**
- Phase 6 transforms the read-only Next.js frontend into an interactive analyst workbench
- Search and conflict endpoints are ready for frontend integration
- Embedding generation activates when EMBEDDING_PROVIDER is set to "openai" or "local"

---

### Phase 6: Interactive Analyst Workbench — Frontend Mutations (2026-03-31)

**What was done:**
- Created typed API client (`lib/api-client.ts`) for all POST/PATCH/DELETE mutations with auth headers
- Added Next.js API proxy via `rewrites` in `next.config.ts` to avoid CORS
- Created comprehensive CSS module (`interactive.module.css`) for all interactive components
- Created CreateCaseModal + CreateCaseButton for case creation from dashboard
- Created DocumentUpload with drag-and-drop, document_kind/source_kind/workstream_domain selectors
- Created IssueManager with inline status/severity editing and auto-scan
- Created ChecklistPanel with SVG coverage ring and inline status toggles
- Created RequestQaPanel for request and Q&A inline status editing
- Created ApprovalPanel for reviewer decisions with optional decision override
- Created RunWorkflowButton for starting workflow runs with optional operator note
- Created LiveRunViewer with SSE EventSource for real-time trace event streaming
- Integrated all interactive components into case workspace and run viewer pages
- Updated dashboard with CreateCaseButton and interactive workbench branding

**Files created:**
- apps/web/src/lib/api-client.ts -- typed mutation client (15 functions, 11 payload types)
- apps/web/src/components/interactive.module.css -- styles for all interactive components
- apps/web/src/components/CreateCaseModal.tsx -- case creation modal form
- apps/web/src/components/CreateCaseButton.tsx -- state wrapper for modal toggle
- apps/web/src/components/DocumentUpload.tsx -- drag-and-drop file upload
- apps/web/src/components/IssueManager.tsx -- inline issue editor + scan button
- apps/web/src/components/ChecklistPanel.tsx -- SVG coverage ring + status toggles
- apps/web/src/components/RequestQaPanel.tsx -- request + Q&A inline editing
- apps/web/src/components/ApprovalPanel.tsx -- reviewer decision form
- apps/web/src/components/RunWorkflowButton.tsx -- run trigger + export
- apps/web/src/components/LiveRunViewer.tsx -- SSE real-time event stream

**Files modified:**
- apps/web/next.config.ts -- API proxy rewrites for /api/v1/*
- apps/web/src/app/page.tsx -- CreateCaseButton integration, updated branding
- apps/web/src/app/cases/[caseId]/page.tsx -- all 6 interactive components integrated
- apps/web/src/app/cases/[caseId]/runs/[runId]/page.tsx -- LiveRunViewer integration
- apps/api/tests/test_phase5_evidence_intelligence.py -- fixed unused imports (ruff lint)

**Decisions made:**
- AD-022: Direct fetch() from client components through Next.js proxy, not Server Actions
- AD-023: router.refresh() for server component revalidation after mutations

**Blockers encountered:**
- None

**Test results:**
- pytest: 71/71 pass (no new backend tests — frontend-only phase)
- eval suites: 11/11 pass (all 5 suites at 100%)
- ruff: clean
- npm lint: clean
- npm typecheck: clean

**Notes for next phase:**
- Phase 7 wires CrewAI agents into the workflow engine
- All API endpoints are now exercisable from the frontend
- SSE live streaming ready for real AI agent trace events

---

<!--
Template for future phases:

### Phase N: Title (YYYY-MM-DD)

**What was done:**
- Item 1
- Item 2

**Files created:**
- path/to/file.py -- description

**Files modified:**
- path/to/file.py -- what changed

**Decisions made:**
- Decision 1: why

**Blockers encountered:**
- None / description

**Test results:**
- pytest: X/X pass
- eval suites: X/X pass
- ruff: clean
- npm lint: clean
- npm typecheck: clean

**Notes for next phase:**
- Any context the next session needs
-->
