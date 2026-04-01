# Master Plan Execution Progress

> This file is the single source of truth for what has been implemented.
> Any AI agent resuming work should read this file + CLAUDE.md first.
> Strategic roadmap comes from `docs/MASTERPLAN.docx` (preferred) and `docs/MASTERPLAN.pdf` (companion export); execution truth comes from the actual repo state.

## Status: Phase 18 In Validation

**Last updated:** 2026-04-01
**Completed phases:** Phase 0, Phase 1, Phase 2, Phase 3, Phase 4, Phase 5, Phase 6, Phase 7, Phase 8, Phase 9, Phase 10, Phase 11, Phase 12, Phase 13, Phase 14, Phase 15, Phase 16, Phase 19, Phase 17
**Next phase:** None in code; final live release validation remains
**Blocking issues:** Docker Desktop daemon unavailable for live prod-stack validation; live OpenRouter and connector validation still needs real credentials / identifiers

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

### Phase 9: Legal / Tax / Regulatory Engine (2026-03-31)

**What was done:**
- Added a shared document-signal utility so multiple domain engines can operate over the same artifact, chunk, and evidence lineage without duplicating parsing glue
- Added a legal engine that extracts directors, DINs, shareholding, subsidiary references, charge signals, and structured contract-clause reviews from uploaded documents
- Added a tax engine that extracts GSTINs, computes tax-area compliance states, applies negation-aware statutory phrase matching, and auto-satisfies relevant checklist items
- Added a sector-aware regulatory engine that builds a compliance matrix across MCA, licensing, and BFSI-specific RBI or SEBI obligations
- Added `GET /cases/{case_id}/legal-summary`, `GET /cases/{case_id}/tax-summary`, and `GET /cases/{case_id}/compliance-matrix`
- Wired Phase 9 refresh into workflow execution before coverage, approvals, syntheses, reports, and CrewAI prompts
- Added compliance-focused CrewAI tools so legal, tax, regulatory, and coordinator agents can inspect structured Phase 9 state directly
- Added a dedicated Phase 9 evaluation suite plus focused pytest coverage for clause extraction, tax statuses, compliance-matrix generation, tool attachment, and workflow integration

**Files created:**
- apps/api/src/.../services/document_signal_utils.py -- shared artifact text snapshot and relevance scoring helpers
- apps/api/src/.../services/legal_service.py -- legal structure and contract review engine
- apps/api/src/.../services/tax_service.py -- tax compliance summary engine
- apps/api/src/.../services/regulatory_service.py -- compliance matrix engine
- apps/api/src/.../agents/compliance_tools.py -- structured legal/tax/regulatory CrewAI tools
- apps/api/tests/test_phase9_legal_tax_regulatory.py -- 5 focused Phase 9 test cases

**Files modified:**
- apps/api/src/.../domain/models.py -- new Phase 9 summary and item models plus `ComplianceStatus`
- apps/api/src/.../api/routes/cases.py -- new legal-summary, tax-summary, and compliance-matrix endpoints
- apps/api/src/.../agents/tools.py -- compliance tool wiring for coordinator and legal/tax/regulatory workstreams
- apps/api/src/.../agents/crew.py -- compact Phase 9 snapshot injection into CrewAI task descriptions
- apps/api/src/.../agents/config.py -- richer legal, tax, and regulatory agent remit definitions
- apps/api/src/.../services/report_service.py -- Phase 9 report note integration
- apps/api/src/.../services/synthesis_service.py -- legal/tax/regulatory narrative enrichment
- apps/api/src/.../services/workflow_service.py -- legal/tax/regulatory refresh and trace integration in deterministic and CrewAI paths
- apps/api/src/.../evaluation/scenarios.py -- Phase 9 scenario and expectation contracts plus updated blocked-scenario baselines
- apps/api/src/.../evaluation/runner.py -- legal/tax/compliance evaluation assertions
- apps/api/tests/test_evaluation.py -- Phase 9 suite registration
- apps/api/src/.../core/settings.py -- current_phase updated to Phase 9 complete

**Decisions made:**
- AD-036: Phase 9 legal, tax, and regulatory summaries are computed on demand and refreshed inside workflows rather than stored as derived tables
- AD-037: Tax and regulatory phrase matching is negation-aware, not naive substring logic
- AD-038: Phase 9 structured state must surface through APIs, workflows, reports, and CrewAI tools together

**Blockers encountered:**
- Initial subsidiary extraction was too greedy and captured trailing sentence text; the regex was tightened before phase closure
- Existing blocked evaluation scenarios needed new open-mandatory baselines because Phase 9 auto-satisfied additional checklist items by design

**Test results:**
- pytest: 97/97 pass (92 existing + 5 new)
- eval suites: 13/13 pass (all 7 suites at 100%)
- ruff: clean
- npm lint: clean
- npm typecheck: clean
- check gate: `./scripts/check.ps1` passed
- dedicated Phase 9 eval artifact: `artifacts/evaluations/phase9-legal-tax-regulatory-20260331T120607Z.json`
- latest full-gate eval artifact: `artifacts/evaluations/all-supported-suites-20260331T121023Z.json`

**Notes for next phase:**
- Phase 10 should build the canonical Commercial / Operations / Cyber / Forensic engine from `MASTERPLAN.docx`
- Phase 9 currently exposes a complete backend, workflow, evaluation, and CrewAI-tooling surface; dedicated analyst UI panels for legal/tax/regulatory depth remain optional future UX depth, not a blocker for canonical Phase 9 closure

---

### Phase 10: Commercial / Operations / Cyber / Forensic Engine (2026-03-31)

**What was done:**
- Added a commercial engine that extracts customer concentration, renewal timing, net revenue retention, churn, and pricing-pressure signals from uploaded evidence
- Added an operations engine that extracts supplier concentration, single-site dependency, key-person dependency, and operational continuity flags
- Added a cyber/privacy engine that evaluates DPDP/security controls, breach history, certification posture, and analyst-readable cyber flags
- Added a forensic engine that detects related-party, round-tripping, revenue-anomaly, and litigation flags from uploaded evidence
- Added `GET /cases/{case_id}/commercial-summary`, `GET /cases/{case_id}/operations-summary`, `GET /cases/{case_id}/cyber-summary`, and `GET /cases/{case_id}/forensic-flags`
- Wired Phase 10 refresh into workflow execution before coverage, syntheses, reports, and CrewAI prompt/tool assembly
- Added Phase 10 CrewAI tools so commercial, operations, cyber/privacy, forensic, and coordinator agents can inspect structured Phase 10 state directly
- Added a dedicated Phase 10 evaluation suite plus focused pytest coverage for endpoints, checklist updates, tool attachment, and workflow integration
- Reconciled older evaluation suites to the integrated post-Phase-10 workflow state so the full gate now reflects actual run-time checklist coverage

**Files created:**
- apps/api/src/.../services/commercial_service.py -- commercial concentration, retention, and pricing-signal engine
- apps/api/src/.../services/operations_service.py -- supplier concentration and dependency engine
- apps/api/src/.../services/cyber_service.py -- DPDP/privacy and security-control engine
- apps/api/src/.../services/forensic_service.py -- forensic flag detection engine
- apps/api/src/.../agents/phase10_tools.py -- structured CrewAI tools for commercial, operations, cyber, and forensic review
- apps/api/tests/test_phase10_commercial_operations_cyber_forensic.py -- 3 focused Phase 10 test cases

**Files modified:**
- apps/api/src/.../domain/models.py -- new CommercialSummary, OperationsSummary, CyberPrivacySummary, ForensicSummary, and supporting Phase 10 item models
- apps/api/src/.../api/routes/cases.py -- new Phase 10 summary and forensic-flag endpoints
- apps/api/src/.../agents/tools.py -- Phase 10 tool wiring for coordinator and domain workstreams
- apps/api/src/.../agents/crew.py -- compact Phase 10 snapshot injection into CrewAI task descriptions
- apps/api/src/.../agents/config.py -- richer commercial, operations, cyber/privacy, and forensic agent remits
- apps/api/src/.../services/report_service.py -- Phase 10 report note integration
- apps/api/src/.../services/synthesis_service.py -- commercial, operations, cyber/privacy, and forensic narrative enrichment
- apps/api/src/.../services/workflow_service.py -- Phase 10 refresh and trace integration in deterministic and CrewAI paths
- apps/api/src/.../services/regulatory_service.py -- tighter vendor-restriction checklist automation focused on licensing/registration evidence
- apps/api/src/.../evaluation/scenarios.py -- Phase 10 scenario and updated integrated checklist expectations for older suites
- apps/api/src/.../evaluation/runner.py -- Phase 10 evaluation assertions and metrics
- apps/api/src/.../core/settings.py -- current_phase updated to Phase 10 complete

**Decisions made:**
- AD-039: Evaluation checklist expectations are measured against the integrated post-run workflow state, not only the standalone endpoint state
- AD-040: Cyber/privacy summaries must present analyst-readable control labels and treat certifications as positive signals only when the underlying control is compliant or partially compliant
- AD-041: `regulatory.vendor_restrictions` checklist automation requires licensing/registration evidence, not arbitrary regulatory signals
- AD-042: Phase 10 structured state must surface through APIs, workflows, reports, and CrewAI tools together

**Blockers encountered:**
- Initial Phase 10 eval closure failed because cyber flags exposed raw control keys and the full workflow auto-satisfied more checklist items than the pre-Phase-10 suite expectations assumed
- Those mismatches were resolved before closure by tightening cyber presentation logic, narrowing regulatory checklist automation, and updating stale eval baselines to the integrated post-run truth

**Test results:**
- pytest: 100/100 pass (97 existing + 3 new)
- eval suites: 14/14 pass (all 8 suites at 100%)
- ruff: clean
- npm lint: clean
- npm typecheck: clean
- check gate: `./scripts/check.ps1` passed
- dedicated Phase 10 eval artifact: `artifacts/evaluations/phase10-commercial-operations-cyber-forensic-20260331T133211Z.json`
- latest full-gate eval artifact: `artifacts/evaluations/all-supported-suites-20260331T133728Z.json`

**Notes for next phase:**
- Start canonical Phase 11 only after confirming its exact title and scope from `MASTERPLAN.docx`
- Phase 10 currently exposes a complete backend, workflow, evaluation, and CrewAI-tooling surface; dedicated analyst UI panels for commercial/operations/cyber/forensic depth remain optional future UX depth, not a blocker for canonical Phase 10 closure

---

### Phase 11: Motion Pack Deepening (2026-03-31)

**What was done:**
- Deepened motion-pack behavior from broad checklist composition into deterministic structured motion-pack analysis for buy-side diligence, credit/lending, and vendor onboarding
- Added a centralized checklist catalog so motion-pack and sector-pack templates compose through one source of truth with duplicate template-key protection
- Added buy-side analysis generation for valuation bridge items, SPA issue matrix items, and PMI risks
- Added borrower scorecard generation for credit/lending with weighted sections, covenant tracking, overall score, and rating
- Added vendor risk tiering for vendor onboarding with score breakdown, questionnaire output, certification requirements, and next-review guidance
- Added `GET /cases/{case_id}/buy-side-analysis`, `GET /cases/{case_id}/borrower-scorecard`, and `GET /cases/{case_id}/vendor-risk-tier`
- Wired Phase 11 refresh into workflow execution so motion-pack state enriches trace events, workstream syntheses, executive memo highlights, and CrewAI prompt/tool surfaces
- Added CrewAI motion-pack specialist prompts and read-only structured review tools for buy-side, credit, and vendor motion-pack outputs
- Added a dedicated Phase 11 evaluation suite plus focused pytest coverage for endpoints, checklist auto-satisfaction, workflow integration, and motion-pack specialist crew attachment
- Reconciled older blocked evaluation suites to the truthful post-run checklist state after Phase 11 deepened workflow coverage

**Files created:**
- apps/api/src/.../services/checklist_catalog.py -- centralized motion-pack and sector-pack checklist catalog
- apps/api/src/.../services/buy_side_service.py -- deterministic buy-side analysis engine
- apps/api/src/.../services/credit_service.py -- deterministic borrower scorecard and covenant tracking engine
- apps/api/src/.../services/vendor_service.py -- deterministic vendor risk-tiering and questionnaire engine
- apps/api/src/.../agents/phase11_tools.py -- structured CrewAI tools for Phase 11 motion-pack review
- apps/api/src/.../agents/packs/__init__.py -- motion-pack specialist package init
- apps/api/src/.../agents/packs/buy_side_crew.py -- buy-side specialist prompt/config
- apps/api/src/.../agents/packs/credit_crew.py -- credit specialist prompt/config
- apps/api/src/.../agents/packs/vendor_crew.py -- vendor specialist prompt/config
- apps/api/tests/test_phase11_motion_pack_deepening.py -- 5 focused Phase 11 test cases

**Files modified:**
- apps/api/src/.../domain/models.py -- new motion-pack analysis, scorecard, valuation, covenant, tiering, and memo-highlight models
- apps/api/src/.../agents/models.py -- MotionPackAnalysisOutput
- apps/api/src/.../agents/tools.py -- motion-pack tool wiring and backward-compatible defaults
- apps/api/src/.../agents/crew.py -- motion-pack specialist crew/task assembly and snapshot injection
- apps/api/src/.../api/routes/cases.py -- new buy-side-analysis, borrower-scorecard, and vendor-risk-tier endpoints
- apps/api/src/.../services/checklist_service.py -- centralized catalog composition and duplicate template-key protection
- apps/api/src/.../services/issue_service.py -- motion-pack-aware heuristic enrichment
- apps/api/src/.../services/report_service.py -- motion-pack highlights in executive memo output
- apps/api/src/.../services/synthesis_service.py -- motion-pack-aware narrative enrichment
- apps/api/src/.../services/workflow_service.py -- motion-pack refresh, trace events, and CrewAI integration
- apps/api/src/.../evaluation/scenarios.py -- Phase 11 scenario contracts and updated integrated checklist expectations
- apps/api/src/.../evaluation/runner.py -- Phase 11 endpoint assertions and reporting
- apps/api/tests/test_evaluation.py -- Phase 11 suite registration
- apps/api/src/.../core/settings.py -- current_phase updated to Phase 11 complete

**Decisions made:**
- AD-043: Motion-pack deepening must be deterministic structured state first, not prompt-only specialization

**Blockers encountered:**
- Initial checklist seeding for deeper motion-pack coverage triggered duplicate `template_key` collisions when motion-pack and sector-pack catalogs overlapped; this was fixed with central catalog composition and dedupe logic before phase closure
- Older blocked evaluation scenarios had to be reconciled to the truthful integrated post-run checklist state because Phase 11 auto-satisfies additional motion-pack items by design

**Test results:**
- pytest: 105/105 pass (100 existing + 5 new)
- eval suites: 17/17 pass (all 9 suites at 100%)
- ruff: clean
- npm lint: clean
- npm typecheck: clean
- check gate: `./scripts/check.ps1` passed
- dedicated Phase 11 eval artifact: `artifacts/evaluations/phase11-motion-pack-deepening-20260331T153537Z.json`
- latest full-gate eval artifact: `artifacts/evaluations/all-supported-suites-20260331T154838Z.json`

**Notes for next phase:**
- Start canonical Phase 12: Sector Pack Deepening from `MASTERPLAN.docx`
- Phase 11 now exposes a complete backend, workflow, report, evaluation, and CrewAI-tooling surface for motion-pack depth; dedicated analyst UI panels for motion-pack-specific valuation bridges, borrower scorecards, and vendor tiering remain future UX depth rather than blockers for canonical Phase 11 closure

---

### Phase 12: Sector Pack Deepening (2026-03-31)

**What was done:**
- Added deterministic sector-pack engines for Tech/SaaS, Manufacturing/Industrials, and BFSI/NBFC on top of the Phase 11 platform spine
- Added structured Tech/SaaS ARR waterfall, NRR, churn, LTV, CAC, and payback extraction with sector-specific flags and checklist automation
- Added structured Manufacturing capacity utilization, DIO/DSO/DPO, asset-turnover, asset-register extraction, sector-specific flags, and checklist automation
- Added structured BFSI/NBFC GNPA, NNPA, CRAR, ALM mismatch, PSL posture, ALM bucket analysis, sector-specific flags, and checklist automation
- Added `GET /cases/{case_id}/tech-saas-metrics`, `GET /cases/{case_id}/manufacturing-metrics`, and `GET /cases/{case_id}/bfsi-nbfc-metrics`
- Wired Phase 12 refresh into workflow execution, trace events, workstream syntheses, executive memo sector highlights, and CrewAI prompt/tool assembly
- Added `agents/phase12_tools.py` so coordinator and relevant workstreams can inspect structured sector metrics directly
- Added a dedicated Phase 12 evaluation suite and focused pytest coverage for endpoints, checklist updates, workflow integration, and CrewAI tool attachment
- Reconciled older evaluation-suite open-mandatory baselines to the truthful post-Phase-12 integrated workflow state

**Files created:**
- apps/api/src/.../services/sector_signal_utils.py -- shared sector-specific extraction helpers for amounts, percentages, days, months, and status flags
- apps/api/src/.../services/tech_saas_service.py -- Tech/SaaS ARR, retention, unit-economics, and checklist automation engine
- apps/api/src/.../services/manufacturing_service.py -- Manufacturing plant, working-capital, asset-register, and checklist automation engine
- apps/api/src/.../services/bfsi_nbfc_service.py -- BFSI/NBFC asset-quality, capital, liquidity, PSL, and checklist automation engine
- apps/api/src/.../agents/phase12_tools.py -- structured CrewAI tools for Tech/SaaS, Manufacturing, and BFSI/NBFC review
- apps/api/tests/test_phase12_sector_pack_deepening.py -- 5 focused Phase 12 test cases

**Files modified:**
- apps/api/src/.../domain/models.py -- new Phase 12 sector summary and supporting metric models
- apps/api/src/.../api/routes/cases.py -- new sector-pack metric endpoints
- apps/api/src/.../agents/tools.py -- Phase 12 tool wiring
- apps/api/src/.../agents/crew.py -- Phase 12 snapshot injection into CrewAI task descriptions
- apps/api/src/.../services/report_service.py -- sector-pack executive memo highlights and narrative enrichment
- apps/api/src/.../services/synthesis_service.py -- sector-pack narrative enrichment by workstream
- apps/api/src/.../services/workflow_service.py -- Phase 12 refresh and trace integration in deterministic and CrewAI paths
- apps/api/src/.../evaluation/scenarios.py -- Phase 12 scenario contracts and updated integrated checklist expectations
- apps/api/src/.../evaluation/runner.py -- Phase 12 endpoint assertions and metrics
- apps/api/tests/test_evaluation.py -- Phase 12 suite registration
- apps/api/src/.../core/settings.py -- current_phase updated to Phase 12 complete

**Decisions made:**
- AD-044: Sector-pack deepening must land as deterministic structured state exposed through APIs, workflows, reports, syntheses, and CrewAI tools together
- AD-045: Sector-pack extractors must deduplicate repeated asset-register and ALM-bucket findings across chunk and evidence surfaces

**Blockers encountered:**
- Initial Tech/SaaS extraction picked `Beginning ARR` instead of `Ending ARR`; extraction order was tightened before closure
- Manufacturing and BFSI sector extractors initially duplicated asset-register rows and ALM bucket rows because the same signals appeared through chunk and evidence text surfaces
- The Phase 12 evaluation suite exposed stale open-mandatory expectations in older suites after Phase 12 legitimately auto-satisfied additional sector-specific checklist items during workflow execution

**Test results:**
- pytest: 110/110 pass (105 existing + 5 new)
- eval suites: 20/20 pass (all 10 suites at 100%)
- ruff: clean
- npm lint: clean
- npm typecheck: clean
- check gate: `./scripts/check.ps1` passed
- dedicated Phase 12 eval artifact: `artifacts/evaluations/phase12-sector-pack-deepening-20260331T163824Z.json`
- latest full-gate eval artifact: `artifacts/evaluations/all-supported-suites-20260331T164647Z.json`

**Notes for next phase:**
- Start canonical Phase 13: Rich Reporting + DOCX/PDF Export from `MASTERPLAN.docx`
- Phase 12 now exposes a complete backend, workflow, report, evaluation, and CrewAI-tooling surface for sector-pack depth; dedicated analyst UI panels for sector-pack detail remain future UX depth rather than blockers for canonical Phase 12 closure

---

### Phase 13: Rich Reporting + DOCX/PDF Export (2026-03-31)

**What was done:**
- Added rich-report rendering with Jinja2 markdown templates for `standard`, `lender`, `board_memo`, and `one_pager` outputs
- Added a dedicated financial annex renderer so Phase 8 QoE state can be exported as a structured analyst appendix
- Added markdown-first DOCX generation with cover page, table of contents, section headings, bullet lists, and table rendering
- Added markdown-first PDF generation with the same report structure and sectioning guarantees
- Persisted `report_template` on workflow runs and expanded report bundles to include full-report markdown, financial-annex markdown, DOCX, and PDF artifacts
- Added `GET /cases/{case_id}/reports/full-report` and `GET /cases/{case_id}/reports/financial-annex`
- Added report-bundle download support and export-package inclusion for stored DOCX/PDF artifacts
- Updated the workbench run trigger and run detail pages so analysts can choose a report template and download rich report artifacts directly
- Added a dedicated Phase 13 evaluation suite plus five focused pytest cases for rendering, binary generation, workflow integration, and export integrity
- Reconciled an older workflow test to the truthful post-Phase-13 bundle contract

**Files created:**
- apps/api/alembic/versions/003_phase13_rich_reporting.py -- schema migration for report-template and rich-bundle metadata
- apps/api/src/.../services/report_markdown.py -- markdown block parsing helpers for downstream renderers
- apps/api/src/.../services/report_renderer.py -- Jinja2 template rendering service for full reports and financial annexes
- apps/api/src/.../services/docx_service.py -- DOCX rendering from markdown
- apps/api/src/.../services/pdf_service.py -- PDF rendering from markdown via reportlab
- apps/api/src/.../templates/standard.md.j2 -- standard full-report template
- apps/api/src/.../templates/lender.md.j2 -- lender report template
- apps/api/src/.../templates/board_memo.md.j2 -- board memo template
- apps/api/src/.../templates/one_pager.md.j2 -- one-pager template
- apps/api/src/.../templates/financial_annex.md.j2 -- financial annex template
- apps/api/tests/test_phase13_rich_reporting.py -- 5 focused Phase 13 test cases

**Files modified:**
- apps/api/pyproject.toml -- added Jinja2 and reportlab dependencies plus template package data
- apps/api/src/.../domain/models.py -- new `ReportTemplateKind`, richer report-bundle metadata, workflow run template field
- apps/api/src/.../db/models.py -- persisted report-template field and binary bundle metadata columns
- apps/api/src/.../services/report_service.py -- rich report context building and artifact generation
- apps/api/src/.../services/workflow_service.py -- persisted report-template handling and rich bundle generation in sync + CrewAI paths
- apps/api/src/.../services/export_service.py -- ZIP export inclusion for rich markdown and binary report artifacts
- apps/api/src/.../api/routes/cases.py -- full-report, financial-annex, and report-bundle download endpoints
- apps/api/src/.../worker.py -- async workflow job template propagation
- apps/api/src/.../evaluation/scenarios.py -- Phase 13 scenario contract and expected export files
- apps/api/src/.../evaluation/runner.py -- rich-reporting evaluation checks and export assertions
- apps/api/tests/test_cases.py -- updated workflow bundle expectations for rich-reporting output
- apps/web/src/lib/api-client.ts -- report-template-aware run and export payloads
- apps/web/src/lib/workbench-data.ts -- template-aware run summaries and rich bundle metadata
- apps/web/src/components/RunWorkflowButton.tsx -- report-template picker in the analyst workbench
- apps/web/src/app/cases/[caseId]/runs/[runId]/page.tsx -- rich bundle download links and template metadata
- apps/api/src/.../core/settings.py -- current_phase updated to Phase 13 complete

**Decisions made:**
- AD-046: rich reporting is markdown-first, with DOCX and PDF derived from the same rendered template output
- AD-047: workflow runs persist report-template choice and store binary report artifacts for later download and export reuse

**Blockers encountered:**
- Initial template rendering failed because the new templates referenced `blocking_issue_count` on checklist coverage instead of the actual `blocker_items` field
- The older workflow test expected only three report bundles; it was updated to assert the truthful richer Phase 13 bundle contract

**Test results:**
- pytest: 115/115 pass (110 existing + 5 new)
- eval suites: 21/21 pass (all 11 suites at 100%)
- ruff: clean
- npm lint: clean
- npm typecheck: clean
- check gate: `./scripts/check.ps1` passed
- dedicated Phase 13 eval artifact: `artifacts/evaluations/phase13-rich-reporting-20260331T173656Z.json`
- latest full-gate eval artifact: `artifacts/evaluations/all-supported-suites-20260331T175355Z.json`

**Notes for next phase:**
- Start canonical Phase 14 from `MASTERPLAN.docx`
- Phase 13 now exposes a complete backend, workflow, export, evaluation, and workbench surface for rich reporting; future report phases should extend the shared markdown-first renderer rather than creating format-specific parallel logic

---

### Phase 14: India Data Connectors (2026-03-31)

**What was done:**
- Added a dedicated source-adapter framework for India connector integrations
- Implemented registered adapters for MCA21, GSTIN, SEBI SCORES, RoC filings, CIBIL stub, and sanctions/watchlist screening
- Added connector catalog metadata with status, credential requirements, fetch support, source kind, and default workstream metadata
- Added `POST /cases/{case_id}/source-adapters/{adapter_id}/fetch` so connector lookups ingest directly into a case as first-class artifacts
- Refactored the ingestion service so uploaded documents and connector-fetched payloads share the same dedup, storage, chunking, evidence extraction, and entity extraction pipeline
- Added a dedicated Phase 14 evaluation suite and focused endpoint tests for connector fetch behavior and downstream legal/tax consumption

**Files created:**
- apps/api/src/.../source_adapters/base.py -- shared adapter contract and stub/live dispatch
- apps/api/src/.../source_adapters/mca21.py -- MCA21 connector
- apps/api/src/.../source_adapters/gstin.py -- GSTIN connector
- apps/api/src/.../source_adapters/sebi_scores.py -- SEBI SCORES connector
- apps/api/src/.../source_adapters/roc.py -- RoC filings connector
- apps/api/src/.../source_adapters/cibil.py -- CIBIL stub connector
- apps/api/src/.../source_adapters/sanctions.py -- sanctions/watchlist connector
- apps/api/src/.../services/source_adapter_service.py -- adapter registry and fetch orchestration
- apps/api/tests/test_phase14_india_connectors.py -- 5 focused Phase 14 test cases

**Files modified:**
- apps/api/src/.../domain/models.py -- source-adapter status enum, fetch request schema, richer adapter summary metadata
- apps/api/src/.../core/settings.py -- connector base-URL/API-key configuration, updated current_phase
- apps/api/src/.../ingestion/adapters/contracts.py -- registry wrapper compatibility layer
- apps/api/src/.../services/ingestion_service.py -- shared connector/upload ingestion path
- apps/api/src/.../api/routes/cases.py -- fetch-and-ingest connector endpoint
- apps/api/src/.../api/routes/source_adapters.py -- live adapter catalog response
- apps/api/src/.../evaluation/scenarios.py -- Phase 14 suite and expectations
- apps/api/src/.../evaluation/runner.py -- connector fetch execution and evaluation assertions
- apps/api/tests/test_source_adapters.py -- updated adapter catalog expectations
- apps/api/tests/test_evaluation.py -- Phase 14 suite registration checks

**Decisions made:**
- AD-048: India connectors ingest through the same artifact/evidence pipeline as uploaded documents
- AD-049: connector completeness requires catalog metadata, fetch endpoints, stub/live status, and evaluation coverage together

**Blockers encountered:**
- The first Phase 14 evaluation run failed because the harness expected `document.id` instead of the actual `artifact.id` returned by `DocumentIngestionResult`; the runner was corrected before closure

**Test results:**
- pytest: 120/120 pass (115 existing + 5 new)
- eval suites: 22/22 pass (all 12 suites at 100%)
- ruff: clean
- npm lint: clean
- npm typecheck: clean
- check gate: `./scripts/check.ps1` passed
- dedicated Phase 14 eval artifact: `artifacts/evaluations/phase14-india-connectors-20260331T185525Z.json`
- latest full-gate eval artifact: `artifacts/evaluations/all-supported-suites-20260331T191237Z.json`

**Notes for next phase:**
- Start canonical Phase 15: Enterprise Security (JWT + Multi-tenancy + Audit) from `MASTERPLAN.docx`
- Future connector work should extend the shared adapter registry and ingestion contract rather than adding one-off API clients

---

### Phase 15: Enterprise Security (JWT + Multi-tenancy + Audit) (2026-04-01)

**What was done:**
- Added first-class organization, API-client, and audit-log persistence to the schema plus a new Alembic migration for tenant-aware upgrades
- Added automatic runtime bootstrap of the default organization and default API client so auth works on fresh databases and migrated databases alike
- Replaced production auth with JWT bearer tokens while preserving header-based auth in `development` and `test`
- Added `POST /api/v1/auth/token` for client-credential token issuance backed by DB-stored API clients
- Added session-scoped org isolation across tenant-scoped ORM models with central query filtering and automatic org stamping on new records
- Added `GET /api/v1/admin/audit-log` for admin-only audit-log access with filters and pagination
- Added audit logging for successful mutations, token issuance, and `401/403` auth failures
- Added rate limiting with Redis-first behavior and automatic in-memory fallback when Redis is unavailable
- Updated worker/runtime paths so seeded defaults and org-aware execution remain valid outside direct request flows
- Added a dedicated Phase 15 pytest tranche for JWT issuance, invalid token rejection, cross-org isolation, audit-log visibility, and rate limiting

**Files created:**
- apps/api/src/.../core/security_utils.py -- client-secret hashing plus JWT encode/decode helpers
- apps/api/src/.../core/rate_limit.py -- Redis-backed rate limiting with in-memory fallback
- apps/api/src/.../services/auth_service.py -- client-credential token issuance and auth audit writes
- apps/api/src/.../services/admin_service.py -- admin audit-log listing service
- apps/api/src/.../services/audit_service.py -- shared manual audit-event writer
- apps/api/src/.../api/routes/auth.py -- `/auth/token`
- apps/api/src/.../api/routes/admin.py -- `/admin/audit-log`
- apps/api/alembic/versions/004_phase15_enterprise_security.py -- tenant/audit schema migration
- apps/api/tests/test_phase15_enterprise_security.py -- 5 focused Phase 15 test cases

**Files modified:**
- apps/api/pyproject.toml -- added `PyJWT`
- .env.example -- expanded runtime contract for org defaults, JWT, and rate limits
- apps/api/src/.../core/settings.py -- added org/bootstrap, JWT, and rate-limit settings; updated current_phase
- apps/api/src/.../domain/models.py -- added org-aware principal plus token and audit DTOs
- apps/api/src/.../api/security.py -- JWT/header-auth dual-mode security and role guards with auth-failure context
- apps/api/src/.../api/dependencies.py -- request/session principal context wiring plus raw DB session dependency
- apps/api/src/.../api/router.py -- mounted auth and admin route families
- apps/api/src/.../db/base.py -- tenant-scoped mixin
- apps/api/src/.../db/models.py -- organization/api-client/audit models plus session-level org filtering and audit hooks
- apps/api/src/.../db/session.py -- runtime default seeding for organization and API client
- apps/api/src/.../main.py -- request ID, rate limiting, auth-failure auditing, and default-seeding startup flow
- apps/api/src/.../services/workflow_service.py -- org-aware run creation when session context is absent
- apps/api/src/.../worker.py -- seeded startup and org-aware background execution
- CLAUDE.md, docs/HANDOFF.md, docs/DECISIONS.md, docs/architecture.md, docs/verification.md, README.md -- Phase 15 continuity updates

**Decisions made:**
- AD-050: Production auth uses JWT; header auth remains available only in `development` and `test`
- AD-051: Org isolation is enforced centrally at the ORM/session layer, not by scattering ad hoc per-route checks
- AD-052: Rate limiting is Redis-first but must degrade to in-memory mode automatically when Redis is unavailable, so tests and local dev remain fast and deterministic

**Blockers encountered:**
- The first tenant-filter implementation scoped relationship loads but not all top-level ORM selects; direct entity where-clauses were added centrally before phase closure
- The initial rate limiter retried Redis on every request when Redis was absent, causing huge test slowdowns; the implementation now switches to memory-only mode after the first Redis failure

**Test results:**
- pytest: 125/125 pass (120 existing + 5 new)
- eval suites: 22/22 pass (all 12 suites at 100%)
- ruff: clean
- npm lint: clean
- npm typecheck: clean
- check gate: `./scripts/check.ps1` passed
- latest full-gate eval artifact: `artifacts/evaluations/all-supported-suites-20260401T011918Z.json`

**Notes for next phase:**
- Start custom Phase 19: Runtime Status + LLM Control Center from the remaining no-loose-ends plan
- Phase 16 is now the live observability baseline; future work should build the status UI, persisted dependency snapshots, and LLM runtime controls on top of the shared probe and telemetry surfaces rather than creating parallel health logic

---

### Phase 16: Platform Observability (structlog + OpenTelemetry + Prometheus) (2026-04-01)

**What was done:**
- Replaced the minimal logging setup with `structlog`, using console-friendly logs in `development` and `test` and JSON logs in `production`
- Added shared telemetry primitives for HTTP requests, workflows, document parsing, document ingestion, connector fetches, dependency probes, exports, and CrewAI-backed LLM runs
- Added OpenTelemetry bootstrapping for FastAPI, SQLAlchemy, and HTTPX with optional OTLP export configuration
- Added root observability endpoints: `GET /api/v1/health/liveness`, `GET /api/v1/health/readiness`, and `GET /api/v1/metrics`
- Reworked readiness reporting to probe the database, Redis, storage, OpenRouter/LLM provider state, and every registered source adapter
- Added non-production-aware readiness semantics so Redis memory fallback and stub connector modes report honestly without failing local development unnecessarily
- Expanded the local Docker stack shape to include Prometheus, Grafana, and Tempo plus provisioning/config files under `ops/observability/`
- Added a dedicated Phase 16 pytest tranche for liveness/readiness/metrics, structured logging behavior, tracing initialization, and production readiness degradation when a required LLM dependency is missing

**Files created:**
- apps/api/src/.../core/telemetry.py -- shared Prometheus metrics and OpenTelemetry initialization helpers
- apps/api/src/.../services/dependency_probe_service.py -- dependency probe and readiness orchestration
- apps/api/tests/test_phase16_observability.py -- 6 focused Phase 16 test cases
- ops/observability/prometheus/prometheus.yml -- Prometheus scrape configuration
- ops/observability/tempo/tempo.yml -- Tempo tracing configuration
- ops/observability/grafana/provisioning/datasources/datasources.yml -- Grafana datasource provisioning
- ops/observability/grafana/provisioning/dashboards/dashboards.yml -- Grafana dashboard provisioning
- ops/observability/grafana/dashboards/.gitkeep -- dashboard placeholder

**Files modified:**
- apps/api/pyproject.toml -- added `structlog`, `prometheus-client`, and OpenTelemetry dependencies compatible with the existing CrewAI stack
- .env.example -- expanded runtime contract for observability, OTLP, Grafana, and OpenRouter dependency probing
- apps/api/src/.../core/settings.py -- added observability settings and updated current phase
- apps/api/src/.../core/logging.py -- structured logging configuration and context binding helpers
- apps/api/src/.../main.py -- request/response instrumentation, structured request logs, telemetry setup, and rate-limit logging
- apps/api/src/.../api/router.py -- mounted the root health router
- apps/api/src/.../api/routes/health.py -- added liveness/readiness/metrics endpoints and preserved `/system/*` compatibility
- apps/api/src/.../domain/models.py -- added dependency/readiness DTOs and enums
- apps/api/src/.../services/ingestion_service.py -- document parse and ingestion metrics
- apps/api/src/.../services/source_adapter_service.py -- connector fetch metrics
- apps/api/src/.../services/export_service.py -- export generation metrics
- apps/api/src/.../services/workflow_service.py -- workflow duration metrics and LLM execution-mode labeling
- apps/api/src/.../agents/crew.py -- LLM-run metrics and OpenRouter-compatible base URL support
- apps/api/tests/test_health.py -- readiness assertions updated for dependency reporting
- docker-compose.yml -- added Prometheus, Grafana, and Tempo services
- scripts/dev-stack.ps1 -- brings up observability services alongside Postgres, Redis, and MinIO
- CLAUDE.md, docs/HANDOFF.md, docs/DECISIONS.md, docs/architecture.md, docs/verification.md, README.md -- Phase 16 continuity updates

**Decisions made:**
- AD-053: Structured logging is environment-shaped, with JSON in production and readable console logs elsewhere
- AD-054: Readiness uses `ok / degraded / failed` plus `live / stub / unconfigured / disabled` modes instead of naive up/down health
- AD-055: Dependency probing is centralized so health endpoints, future status UI, and later operational phases share the same truth

**Blockers encountered:**
- Live startup of the new observability containers could not be verified in-session because Docker Desktop was not running locally and the current shell could not start the Windows service
- The observability dependency install initially conflicted with CrewAI's OpenTelemetry pin range; the dependencies were repinned to a CrewAI-compatible OpenTelemetry family before closure

**Test results:**
- pytest: 131/131 pass (125 existing + 6 new)
- eval suites: 22/22 pass (all 12 suites at 100%)
- ruff: clean
- npm lint: clean
- npm typecheck: clean
- check gate: `./scripts/check.ps1` passed
- `docker compose config`: passed for the expanded observability stack
- latest full-gate eval artifact: `artifacts/evaluations/all-supported-suites-20260401T024644Z.json`

**Notes for next phase:**
- Start custom Phase 19: Runtime Status + LLM Control Center using the new shared dependency-probe and telemetry surfaces
- Keep the Phase 16 readiness model as the single dependency truth; do not build a second ad hoc status implementation for the UI

---

### Phase 19: Runtime Status + LLM Control Center (2026-04-01)

**What was done:**
- Added persisted dependency snapshots so runtime status survives beyond a single readiness request and can power operator-facing UI
- Added admin/runtime APIs for dependency refresh, dependency listing, provider catalog listing, and org-scoped default LLM configuration
- Added OpenRouter model discovery with live fetch, filtering for tool-capable text models, memory + Redis cache, and graceful fallback when unavailable
- Added per-run LLM provider/model overrides and persisted the effective provider/model on workflow runs so queued and completed runs record the actual runtime used
- Updated the worker path so queued runs reuse the original run record and keep the resolved runtime contract instead of implicitly re-resolving inside the worker
- Added a recurring worker cron job that refreshes dependency snapshots every 5 minutes through the shared dependency-probe service
- Added a dedicated `/status` workbench screen with dependency status cards, manual refresh, org-level LLM default controls, and analyst-visible runtime state
- Extended the existing run trigger and run viewer so analysts can set runtime overrides per run and later see the effective provider/model used
- Restored backward compatibility for earlier CrewAI phases by keeping legacy `_crew_available()`-based execution tests valid while preserving the Phase 19 runtime-resolution order

**Files created:**
- apps/api/src/.../services/runtime_control_service.py -- org default LLM config, OpenRouter catalog discovery, runtime resolution, and fail-fast live-runtime checks
- apps/api/alembic/versions/005_phase19_runtime_status_and_llm_control.py -- schema changes for dependency snapshots, org runtime config, and workflow runtime persistence
- apps/api/tests/test_phase19_runtime_control.py -- 6 focused Phase 19 test cases
- apps/web/src/components/StatusControlCenter.tsx -- interactive runtime status and LLM control surface
- apps/web/src/app/status/page.tsx -- workbench `/status` screen

**Files modified:**
- apps/api/src/.../domain/models.py -- added dependency/LLM runtime DTOs and workflow override fields
- apps/api/src/.../db/models.py -- added `DependencyStatusRecord`, `OrgRuntimeConfigRecord`, and workflow runtime columns
- apps/api/src/.../db/session.py -- bootstraps org runtime config alongside seeded org/auth defaults
- apps/api/src/.../services/dependency_probe_service.py -- refresh-and-persist path plus latest snapshot retrieval
- apps/api/src/.../services/workflow_service.py -- effective runtime persistence, queue compatibility, legacy CrewAI fallback bridge
- apps/api/src/.../agents/crew.py -- explicit provider/model runtime injection with backward-compatible defaults
- apps/api/src/.../api/routes/health.py -- read surfaces for dependency status and LLM provider/default state
- apps/api/src/.../api/routes/admin.py -- admin refresh, provider catalog, and org-default runtime controls
- apps/api/src/.../api/routes/cases.py -- fail-fast `503` on explicitly requested unavailable live runtime
- apps/api/src/.../worker.py -- 5-minute dependency refresh cron and queued-run execution over persisted runtime metadata
- apps/api/src/.../core/settings.py -- current phase and model-catalog cache setting
- .env.example -- Phase 19 runtime-control settings
- apps/web/src/lib/api-client.ts -- protected client functions for dependency/LLM admin surfaces and run overrides
- apps/web/src/lib/workbench-data.ts -- status workspace loader and updated demo/runtime fallbacks
- apps/web/src/components/RunWorkflowButton.tsx -- per-run provider/model override UI
- apps/web/src/app/cases/[caseId]/runs/[runId]/page.tsx -- effective runtime display on run detail
- apps/web/src/app/page.tsx -- linked `/status` entry point
- apps/web/src/components/interactive.module.css -- supporting styles for runtime controls
- CLAUDE.md, docs/HANDOFF.md, docs/DECISIONS.md, docs/architecture.md, docs/verification.md, README.md -- Phase 19 continuity updates

**Decisions made:**
- AD-056: Runtime dependency status is persisted as the latest snapshot only; historical uptime charts remain out of scope for Phase 19
- AD-057: LLM runtime resolution order is per-run override -> org default -> environment fallback -> deterministic fallback
- AD-058: OpenRouter is exposed as the first live model-catalog provider and must be filtered to tool-capable text models before reaching the UI
- AD-059: Queued workflow runs persist the effective provider/model so worker execution cannot drift from the run created at enqueue time

**Blockers encountered:**
- The first Phase 19 test pass exposed queue-argument drift and earlier CrewAI test regressions; both were fixed by aligning the test contract and restoring backward-compatible runtime behavior in code instead of weakening the new Phase 19 runtime model
- OpenRouter live behavior is wired and test-covered through mocked HTTP/catalog paths, but full live-provider validation remains intentionally deferred to canonical Phase 17

**Test results:**
- pytest: 137/137 pass (131 existing + 6 new)
- eval suites: 22/22 pass (all 12 suites at 100%)
- ruff: clean
- npm lint: clean
- npm typecheck: clean
- check gate: `./scripts/check.ps1` passed
- latest full-gate eval artifact: `artifacts/evaluations/all-supported-suites-20260401T040707Z.json`

**Notes for next phase:**
- Start canonical Phase 17: Evaluation Deepening + Red-Teaming
- Use the new dependency snapshot store, provider catalog APIs, and persisted run runtime metadata as the baseline for live OpenRouter benchmarking and live connector validation

---

### Phase 17: Evaluation Deepening + Red-Teaming (2026-04-01)

**What was done:**
- Expanded the evaluation corpus from 22 to 30 scenarios, covering all active `motion_pack x sector_pack` combinations plus adversarial uploaded-content cases
- Added per-scenario quality scorecards with completeness, accuracy, hallucination-rate, citation-coverage, and overall-score fields
- Added suite-level and combined-report quality summaries so evaluation output is no longer only pass/fail
- Added optional live validation suites for OpenRouter benchmarking and live connector fetch validation, with explicit skip behavior when credentials or identifiers are not configured
- Added a repeatable load benchmark over the real ASGI app for `GET /system/health`, `POST /issues/scan`, and `POST /search`
- Added regression-baseline generation and comparison logic with a committed baseline file under `artifacts/baselines/`
- Updated the repo gate so `./scripts/check.ps1` now runs pytest, the expanded evaluation suite, the load benchmark, and the regression comparison automatically

**Files created:**
- apps/api/src/.../evaluation/live_validation.py -- optional live OpenRouter benchmark and live connector validation suites
- apps/api/src/.../evaluation/performance.py -- repeatable in-process ASGI load benchmark
- apps/api/src/.../evaluation/regression.py -- baseline generation and regression comparison
- apps/api/tests/test_phase17_evaluation_deepening.py -- focused Phase 17 tests
- artifacts/baselines/all-supported-suites-baseline.json -- committed evaluation regression baseline

**Files modified:**
- apps/api/src/.../domain/models.py -- added `QualityScorecard`
- apps/api/src/.../evaluation/runner.py -- scenario scorecards, aggregate quality summaries, scenario duration metrics
- apps/api/src/.../evaluation/scenarios.py -- added Phase 17 matrix + red-team scenarios, bringing total scenario count to 30
- apps/api/tests/test_evaluation.py -- expanded suite coverage assertions
- scripts/check.ps1 -- added performance benchmark and regression baseline gate; optional live validation hook
- .env.example, CLAUDE.md, docs/HANDOFF.md, docs/DECISIONS.md, docs/architecture.md, docs/verification.md, README.md -- Phase 17 continuity updates

**Decisions made:**
- AD-060: Phase 17 quality evaluation uses scorecards plus regression baselines, not only pass/fail scenario counts
- AD-061: Live OpenRouter and connector validation are optional in the default gate and become hard failures only when explicitly required
- AD-062: The Phase 17 performance gate uses repeatable in-process ASGI benchmarks as the regression guardrail for this repo

**Blockers encountered:**
- None in code. The optional live validation suites ran in skip mode because no live OpenRouter credentials or connector identifiers were configured in the environment

**Test results:**
- pytest: 142/142 pass (137 existing + 5 new)
- eval suites: 30/30 pass (all 13 suites at 100%)
- load benchmark: passed (`system_health_p95=22.54ms`, `issues_scan_p95=165.09ms`, `search_p95=30.04ms`)
- regression baseline: passed against `artifacts/baselines/all-supported-suites-baseline.json`
- optional live validation: executed in skip mode with `0 failed`, `7 skipped`
- ruff: clean
- npm lint: clean
- npm typecheck: clean
- check gate: `./scripts/check.ps1` passed
- latest full-gate eval artifact: `artifacts/evaluations/all-supported-suites-20260401T045136Z.json`
- latest load artifact: `artifacts/evaluations/phase17-load-benchmark-20260401T045153Z.json`
- latest live-validation artifacts: `artifacts/evaluations/phase17-live-connectors-20260401T043440Z.json`, `artifacts/evaluations/phase17-openrouter-benchmark-20260401T043440Z.json`

**Notes for next phase:**
- Start canonical Phase 18: Hardening + Release Packaging
- Keep the Phase 17 baseline file current when the evaluation corpus changes materially, and use `PHASE17_REQUIRE_LIVE_VALIDATION=true` when moving toward production-ready live-provider validation

---

### Phase 18: Hardening + Release Packaging (2026-04-01)

**What was done:**
- Added multi-stage production Dockerfiles for the FastAPI API and the Next.js workbench, plus production-image builds for Prometheus, Grafana, and Tempo
- Added `docker-compose.prod.yml` with named volumes only, a dedicated migration service, resource limits, health checks, and production-shaped API, worker, web, storage, and observability wiring
- Added generated API-reference documentation from the live FastAPI OpenAPI schema
- Added backup and restore automation with dry-run support, retention handling, and optional S3/MinIO upload parameters
- Added production-aware smoke and validation scripts, including JWT-based smoke support and a clean skip path when the Docker daemon is unavailable
- Strengthened the repo gate so it now also validates the production compose config, regenerates the API reference, runs backup dry-run, and performs a full Next.js production build

**Files created:**
- .dockerignore -- shared production build exclusions for root-context Docker builds
- apps/api/Dockerfile -- multi-stage non-root API image
- apps/web/Dockerfile -- standalone Next.js production image
- ops/observability/prometheus/Dockerfile -- production Prometheus image with baked config
- ops/observability/grafana/Dockerfile -- production Grafana image with baked provisioning
- ops/observability/tempo/Dockerfile -- production Tempo image with baked config
- docker-compose.prod.yml -- production compose stack with migrate/api/worker/web/observability services
- scripts/generate_api_reference.py -- OpenAPI-to-Markdown generator
- scripts/generate-api-reference.ps1 -- PowerShell wrapper for API-reference generation
- scripts/backup-db.ps1 -- production backup automation with dry-run and optional upload support
- scripts/restore-db.ps1 -- restore automation with dry-run support
- scripts/validate-prod-stack.ps1 -- live production-stack validator with honest skip/fail behavior
- apps/api/tests/test_phase18_release_packaging.py -- focused Phase 18 packaging tests
- docs/api-reference.md -- generated API contract

**Files modified:**
- scripts/check.ps1 -- production packaging checks and Next.js build
- scripts/smoke.ps1 -- JWT mode for production-shaped smoke testing
- apps/web/next.config.ts -- standalone output for production container builds
- .env.example -- expanded production environment contract
- apps/api/src/.../core/settings.py -- Phase 18 runtime phase string
- apps/web/src/lib/workbench-data.ts -- Phase 18 fallback phase string
- CLAUDE.md, docs/HANDOFF.md, docs/DECISIONS.md, docs/architecture.md, docs/verification.md, docs/deployment.md, docs/runbook.md, docs/release-checklist.md, README.md -- Phase 18 continuity and release-doc updates

**Decisions made:**
- AD-063: Production packaging uses multi-stage non-root images and a dedicated migration service rather than schema auto-create at runtime
- AD-064: API-reference documentation is generated from the live OpenAPI schema and refreshed by the standard repo gate
- AD-065: Production-stack boot validation is optional by default and becomes strict only when explicitly required in a live environment
- AD-066: Backup and restore automation prefer direct `pg_dump` / `psql` when available and fall back to Docker-based execution only when needed

**Blockers encountered:**
- No code blockers. Live production-stack boot validation could not be completed because the Docker Desktop daemon was unavailable from the current shell
- Strict OpenRouter and connector live validation is still environment-dependent and needs real credentials / identifiers to move from skip mode to required mode

**Test results:**
- pytest: 147/147 pass
- eval suites: 30/30 pass (all 13 suites at 100%)
- load benchmark: passed (`system_health_p95=20.9ms`, `issues_scan_p95=223.51ms`, `search_p95=38.24ms`)
- regression baseline: passed against `artifacts/baselines/all-supported-suites-baseline.json`
- npm lint: clean
- npm typecheck: clean
- npm build: clean
- prod compose config: `docker compose -f docker-compose.prod.yml config` passed
- API reference generation: `./scripts/generate-api-reference.ps1` passed
- backup dry-run: `./scripts/backup-db.ps1 -DryRun` passed
- live prod-stack validation: `./scripts/validate-prod-stack.ps1` skipped cleanly because Docker Desktop was unavailable
- check gate: `./scripts/check.ps1` passed
- latest full-gate eval artifact: `artifacts/evaluations/all-supported-suites-20260401T063655Z.json`
- latest load artifact: `artifacts/evaluations/phase17-load-benchmark-20260401T063713Z.json`

**Notes for next phase:**
- No canonical implementation phases remain
- To call the whole project fully production-ready, run `PHASE17_REQUIRE_LIVE_VALIDATION=true ./scripts/check.ps1` with real OpenRouter and connector credentials configured
- Then run `./scripts/validate-prod-stack.ps1 -RequireLive` in an environment where the Docker daemon is reachable

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
