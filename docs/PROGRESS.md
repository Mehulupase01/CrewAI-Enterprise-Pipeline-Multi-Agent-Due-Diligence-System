# Master Plan Execution Progress

> This file is the single source of truth for what has been implemented.
> Any AI agent resuming work should read this file + CLAUDE.md first.
> Strategic roadmap comes from `docs/MASTERPLAN.docx` (preferred) and `docs/MASTERPLAN.pdf` (companion export); execution truth comes from the actual repo state.

## Status: Phase 8 Complete + Post-Phase-7 Enhancement Landed

**Last updated:** 2026-03-31
**Completed phases:** Phase 0, Phase 1, Phase 2, Phase 3, Phase 4, Phase 5, Phase 6, Phase 7, Phase 8
**Next phase:** Phase 9 (Legal / Tax / Regulatory Engine)
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

### Phase 7: CrewAI Multi-Agent Orchestration (2026-03-31)

**What was done:**
- Created `agents/` package with config, models, and crew factory
- Defined 9 workstream-specific agent configs (role, goal, backstory) — India-focused, domain-expert personas
- Defined coordinator agent for executive synthesis across all workstreams
- Added motion_pack and sector_pack context helpers for agent prompt enrichment
- Created structured Pydantic output models: WorkstreamAnalysisOutput, ExecutiveSummaryOutput
- Built CaseContext data loader that pre-queries all case data before crew kickoff
- Built crew factory: creates one Agent+Task per active workstream + coordinator summary task
- Integrated CrewAI into WorkflowService.execute_run() with deterministic fallback (AD-001)
- When LLM_PROVIDER + LLM_API_KEY are set → CrewAI agents analyze each workstream
- When no LLM → existing deterministic template logic runs (zero regression)
- Crew runs via asyncio.to_thread(crew.kickoff) to avoid blocking async event loop
- Crew output is parsed into WorkstreamSynthesisRecords + ReportBundleRecords + RunTraceEventRecords
- Added robust status normalization for LLM-produced workstream status strings
- Added fallback handling when agent output isn't structured (raw text capture)
- Added 5 new LLM settings: llm_provider, llm_api_key, llm_model, crew_verbose, crew_max_rpm
- Updated current_phase to "Phase 7: CrewAI Multi-Agent Orchestration"
- Added 12 new pytest tests

**Files created:**
- apps/api/src/.../agents/__init__.py -- package init
- apps/api/src/.../agents/config.py -- 9 workstream agent configs + coordinator + pack context helpers
- apps/api/src/.../agents/models.py -- WorkstreamAnalysisOutput, ExecutiveSummaryOutput
- apps/api/src/.../agents/crew.py -- CaseContext, build_case_context, build_due_diligence_crew, run_crew
- apps/api/tests/test_phase7_crewai_orchestration.py -- 12 test cases

**Files modified:**
- apps/api/src/.../core/settings.py -- 5 new LLM settings, updated current_phase
- apps/api/src/.../services/workflow_service.py -- CrewAI branch with _execute_crew_run + deterministic fallback refactored into _execute_deterministic_run

**Decisions made:**
- AD-024: CrewAI agents use sequential process — each workstream runs independently, then coordinator synthesizes all outputs. Hierarchical process adds complexity without benefit at this scale.
- AD-025: Agent context is pre-loaded (queried once before kickoff) rather than using custom tools. This avoids async/sync bridging and makes the system testable without LLM calls.
- AD-026: Crew runs in a thread via asyncio.to_thread(crew.kickoff) to avoid blocking the async event loop. Trace events are written after completion, not streamed mid-execution.
- AD-027: LLM settings default to none/null — identical to AD-001 and AD-020 pattern. CrewAI only activates with explicit configuration.

**Blockers encountered:**
- None

**Test results:**
- pytest: 83/83 pass (71 existing + 12 new)
- eval suites: 11/11 pass (all 5 suites at 100%)
- ruff: clean
- npm lint: clean
- npm typecheck: clean

**Notes for next phase:**
- CrewAI is wired but requires LLM_PROVIDER + LLM_API_KEY env vars to activate
- All 71 existing tests continue to pass unchanged (deterministic fallback)
- Trace events include crew_initialized, agent_{workstream}, coordinator_synthesis when CrewAI is active
- Agent prompts are India-focused and motion_pack/sector_pack-aware
- No custom CrewAI tools yet — agents receive all context in task descriptions

---

### Post-Phase-7 Enhancement: Tool-Grounded CrewAI Evidence Access (2026-03-31)

**What was done:**
- Added scoped read-only CrewAI tools for evidence search, issue review, and checklist-gap review
- Shifted the CrewAI path from large prompt stuffing to compact snapshots plus tool-based drill-down
- Extended case context building to preload document chunks and link them back to evidence-bearing workstreams
- Added post-run trace summaries for tool usage at the workstream and coordinator levels
- Preserved the deterministic fallback path unchanged and fully covered by the existing test/eval safety net
- Added 4 new pytest tests covering tool behavior and traced CrewAI runs

**Files created:**
- apps/api/src/.../agents/tools.py -- scoped read-only CrewAI tools with usage logging
- apps/api/tests/test_phase8_crewai_tools.py -- Phase 8 unit/integration tests

**Files modified:**
- apps/api/src/.../agents/crew.py -- chunk-aware case context, compact prompts, scoped tool attachment
- apps/api/src/.../services/workflow_service.py -- tool-usage trace summaries and richer CrewAI run metadata
- apps/api/src/.../services/case_service.py -- eager-load document chunks for CrewAI case context
- apps/api/src/.../core/settings.py -- current_phase updated, added crew_tool_top_k and crew_tool_max_usage
- apps/api/tests/test_phase7_crewai_orchestration.py -- updated for chunk-aware context and tool-bearing crew builds

**Decisions made:**
- AD-030: CrewAI tools operate on pre-loaded case snapshots rather than live async DB queries
- AD-031: Tool usage is summarized in persisted run traces after crew completion

**Blockers encountered:**
- `MASTERPLAN.pdf` is image-based in the local environment, so the exact Phase 8 wording could not be extracted mechanically; implementation target was reconciled from repo truth plus the recorded roadmap direction

**Test results:**
- pytest: 87/87 pass (83 existing + 4 new)
- eval suites: 11/11 pass (all 5 suites at 100%)
- ruff: clean
- npm lint: clean
- npm typecheck: clean
- check gate: `./scripts/check.ps1` passed
- latest evaluation artifact: `artifacts/evaluations/all-supported-suites-20260331T102831Z.json`

**Notes for next canonical phase:**
- CrewAI now has scoped evidence/issue/checklist tools, but trace events are still persisted after completion rather than streamed mid-run
- The next master-plan phase remains Phase 8: Financial Quality of Earnings (QoE) Engine

---

### Phase 8: Financial Quality of Earnings (QoE) Engine (2026-03-31)

**What was done:**
- Added structured financial statement parsing for XLSX financial workbooks, including annual period normalization for revenue, EBITDA, PAT, operating cash flow, debt, interest, working capital, total assets, equity, customer concentration, and Q4 revenue share
- Added QoE adjustment extraction for one-time and non-recurring items and a normalized EBITDA bridge
- Added a dedicated Phase 8 service that builds on-demand financial summaries from uploaded artifacts and computes core ratios for diligence and underwriting
- Added automatic red-flag detection for customer concentration, negative cash conversion, declining revenue growth, Q4 seasonality, leverage pressure, and low interest coverage
- Added automatic checklist satisfaction for relevant financial workstream items, with persisted notes and an opt-out query flag for dry-run access
- Added `GET /cases/{case_id}/financial-summary` and wired the financial summary refresh into workflow execution before coverage, approvals, syntheses, and report generation
- Added CrewAI-facing financial tools and sector benchmarks so the financial workstream and coordinator can use the structured QoE state instead of relying only on narrative prompt context
- Added a dedicated Phase 8 evaluation suite plus focused pytest coverage for parsing, ratios, checklist auto-satisfaction, tool attachment, and workflow integration

**Files created:**
- apps/api/src/.../ingestion/financial_parser.py -- structured XLSX financial parser and QoE adjustment extraction
- apps/api/src/.../services/financial_qoe_service.py -- financial summary, ratio, flag, and checklist automation service
- apps/api/src/.../agents/financial_tools.py -- financial ratio review and sector benchmark tools for CrewAI
- apps/api/src/.../evaluation/financial_fixtures.py -- reusable financial workbook fixture generator
- apps/api/tests/test_phase8_financial_qoe.py -- 5 focused Phase 8 test cases

**Files modified:**
- apps/api/src/.../domain/models.py -- new FinancialPeriod, QoEAdjustment, FinancialStatement, FinancialMetricSummary, ChecklistAutoUpdate
- apps/api/src/.../api/routes/cases.py -- GET /cases/{id}/financial-summary
- apps/api/src/.../services/report_service.py -- financial QoE note integration
- apps/api/src/.../services/synthesis_service.py -- financial narrative enrichment
- apps/api/src/.../services/workflow_service.py -- financial summary refresh in deterministic and CrewAI run paths
- apps/api/src/.../agents/tools.py -- financial tool wiring for coordinator and financial workstream
- apps/api/src/.../agents/crew.py -- financial summary prompt/context injection
- apps/api/src/.../agents/config.py -- richer financial QoE agent remit
- apps/api/src/.../evaluation/scenarios.py -- Phase 8 scenario and expectation contracts
- apps/api/src/.../evaluation/runner.py -- financial summary evaluation assertions
- apps/api/tests/test_evaluation.py -- Phase 8 suite registration

**Decisions made:**
- AD-032: `MASTERPLAN.docx` is the canonical machine-readable roadmap source; the PDF remains a companion export
- AD-033: Financial summaries are computed from stored artifacts on demand and refreshed inside workflows rather than persisted as a separate derived table
- AD-034: Financial metric labels prefer exact and longer alias matches over generic substrings to avoid misclassifying EBITDA and seasonality rows
- AD-035: `GET /financial-summary` persists checklist auto-satisfaction by default, with `persist_checklist=false` available for dry-run access

**Blockers encountered:**
- Initial parser alias matching was too greedy (`EBITDA` could be consumed by `EBIT`, and `Q4 Revenue Share` by `revenue`); this was fixed before phase closure

**Test results:**
- pytest: 92/92 pass (87 existing + 5 new)
- eval suites: 12/12 pass (all 6 suites at 100%)
- ruff: clean
- npm lint: clean
- npm typecheck: clean
- check gate: `./scripts/check.ps1` passed
- dedicated Phase 8 eval artifact: `artifacts/evaluations/phase8-financial-qoe-20260331T112934Z.json`
- latest full-gate eval artifact: `artifacts/evaluations/all-supported-suites-20260331T112825Z.json`

**Notes for next phase:**
- Phase 9 should build the canonical Legal / Tax / Regulatory engine from `MASTERPLAN.docx`
- Phase 8 currently exposes a complete backend and workflow surface; a dedicated frontend financial summary panel is still optional future UX depth, not a blocker for canonical Phase 8 closure

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
