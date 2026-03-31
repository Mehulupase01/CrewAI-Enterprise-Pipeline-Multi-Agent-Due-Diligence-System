# Architecture Overview

> **Last updated:** 2026-03-31 (Phase 14 complete)
> **Update rule:** This file is updated after every masterplan phase to reflect actual system state.

## System Summary

India-focused due diligence operating system: FastAPI control plane + Next.js analyst workbench.
Manages diligence cases, document ingestion, evidence extraction, issue flags, checklist coverage,
reviewer approvals, workflow runs, report bundles, and durable ZIP export packages.

## Architecture Diagram

See `docs/MASTERPLAN.docx` (preferred) or `docs/MASTERPLAN.pdf` for the roadmap diagrams including:
- System architecture (all components and connections)
- 7-step data flow pipeline
- Phase dependency graph
- CrewAI multi-agent architecture (target state)
- Pack model matrix
- Database ER diagram

## Current State (Honest Assessment)

### What is REAL and WORKING
- 14 SQLAlchemy ORM models with proper relationships, cascades, timestamps
- 116 domain models and enums with consistent naming conventions across API, workflow, and evaluation surfaces
- 29 service and engine classes + 6 concrete source adapters + CrewAI multi-agent orchestration (activates with LLM config)
- 65 REST endpoints (full CRUD + SSE streaming + chunks + search + conflicts + financial/legal/tax/compliance plus Phase 10 summaries, Phase 11 motion-pack endpoints, Phase 12 sector-pack endpoints, rich-report previews, report-bundle downloads, and Phase 14 connector fetches)
- Document parsing for 6 formats (PDF with tables, DOCX with headings+tables, XLSX multi-sheet, CSV, JSON, TXT)
- Structured financial workbook parsing for annual periods, QoE adjustments, normalized EBITDA, ratios, and financial flags
- Structured legal, tax, and regulatory parsing for directors, DINs, shareholding, contract clauses, GST posture, and compliance-matrix generation
- Registered India source adapters for MCA21, GSTIN, SEBI SCORES, RoC filings, CIBIL stub, and sanctions screening
- Semantic chunking engine (heading > paragraph > sentence splitting, 1200 char max)
- Rule-based entity extraction (financial, legal, regulatory, India identifiers)
- SHA256 document dedup (same content returns existing artifact)
- Header-based RBAC with 4 roles (VIEWER, ANALYST, REVIEWER, ADMIN)
- Evaluation harness with 12 suites, 22 scenarios
- 120 pytest unit tests
- Export ZIP packages (markdown, DOCX, PDF, plus JSON metadata / snapshots)
- Docker Compose stack (PostgreSQL 17, Redis 7.4, MinIO)

### What was ADDED after Phase 7
- Scoped read-only CrewAI tools (`agents/tools.py`) for evidence search, issue review, and checklist-gap review
- Chunk-aware case context loading so tools can inspect document excerpts without live DB access
- Compact workstream and coordinator prompts that rely on tool usage instead of prompt-stuffing the full case state
- Persisted tool-usage summaries in run trace events plus total tool-call counts in CrewAI run summaries
- 4 new pytest tests covering tool behavior and traced CrewAI runs

### What was ADDED in Phase 8
- `ingestion/financial_parser.py` for structured XLSX financial statement extraction and QoE adjustment detection
- `services/financial_qoe_service.py` for on-demand financial summaries, ratio computation, normalized EBITDA bridge, red-flag detection, and checklist auto-satisfaction
- `GET /cases/{id}/financial-summary` for analysts, evaluators, and workflow orchestration
- Workflow-integrated financial refresh so approvals, syntheses, CrewAI prompts, and executive reporting all consume the same structured QoE state
- `agents/financial_tools.py` plus financial prompt context so the CrewAI financial workstream and coordinator can use ratios and sector benchmarks directly
- Dedicated Phase 8 evaluation coverage and five focused pytest cases for parser, ratios, checklist automation, tool attachment, and workflow integration

### What was ADDED in Phase 9
- `services/document_signal_utils.py` so legal, tax, and regulatory engines can operate over shared artifact text snapshots with chunk and evidence lineage
- `services/legal_service.py` for director, DIN, shareholding, subsidiary, charge, and contract-clause extraction plus legal checklist automation
- `services/tax_service.py` for GSTIN extraction, tax-area compliance assessment, negation-aware statutory signal matching, and tax checklist automation
- `services/regulatory_service.py` for sector-aware compliance matrix generation across MCA, licensing, DPDP, factory/EHS, RBI, and SEBI-style regimes
- `GET /cases/{id}/legal-summary`, `GET /cases/{id}/tax-summary`, and `GET /cases/{id}/compliance-matrix`
- Workflow-integrated legal/tax/regulatory refresh so syntheses, reports, trace events, and CrewAI prompts consume the same Phase 9 state
- `agents/compliance_tools.py` plus compliance prompt context so legal, tax, regulatory, and coordinator agents can drill into structured Phase 9 outputs directly
- Dedicated Phase 9 evaluation coverage and five focused pytest cases for clause extraction, tax statuses, compliance-matrix generation, tool attachment, and workflow integration

### What was ADDED in Phase 10
- `services/commercial_service.py` for customer concentration, renewal timing, NRR, churn, pricing-pressure analysis, and checklist automation
- `services/operations_service.py` for supplier concentration, single-site dependency, key-person dependency, and continuity-risk analysis
- `services/cyber_service.py` for DPDP/privacy control review, certification posture, breach history, analyst-readable cyber flags, and checklist automation
- `services/forensic_service.py` for structured related-party, round-tripping, revenue-anomaly, and litigation flag detection plus checklist automation
- `GET /cases/{id}/commercial-summary`, `GET /cases/{id}/operations-summary`, `GET /cases/{id}/cyber-summary`, and `GET /cases/{id}/forensic-flags`
- Workflow-integrated Phase 10 refresh so syntheses, reports, trace events, and CrewAI prompts consume the same structured commercial/operations/cyber/forensic state
- `agents/phase10_tools.py` plus phase-aware prompt context so commercial, operations, cyber/privacy, forensic, and coordinator agents can drill into structured Phase 10 outputs directly
- Dedicated Phase 10 evaluation coverage and three focused pytest cases for summary extraction, tool attachment, checklist automation, and workflow integration

### What was ADDED in Phase 11
- `services/checklist_catalog.py` as the centralized motion-pack and sector-pack checklist source of truth with duplicate template-key protection
- `services/buy_side_service.py` for deterministic valuation bridge, SPA issue matrix, PMI risk generation, and related checklist automation
- `services/credit_service.py` for deterministic borrower scorecard, covenant tracking, and credit checklist automation
- `services/vendor_service.py` for deterministic vendor risk-tiering, questionnaire generation, certification requirements, and onboarding checklist automation
- `GET /cases/{id}/buy-side-analysis`, `GET /cases/{id}/borrower-scorecard`, and `GET /cases/{id}/vendor-risk-tier`
- Workflow-integrated Phase 11 refresh so syntheses, reports, trace events, and CrewAI prompts consume the same structured motion-pack state
- `agents/phase11_tools.py` plus `agents/packs/*.py` so buy-side, credit, and vendor motion-pack specialists can review structured Phase 11 outputs directly
- Dedicated Phase 11 evaluation coverage and five focused pytest cases for endpoint behavior, checklist automation, crew attachment, and workflow integration

### What was ADDED in Phase 12
- `services/sector_signal_utils.py` as the shared extraction helper layer for sector metrics, durations, and status phrases
- `services/tech_saas_service.py` for deterministic ARR waterfall, NRR, churn, LTV, CAC, payback, sector flags, and checklist automation
- `services/manufacturing_service.py` for deterministic capacity utilization, DIO/DSO/DPO, asset-register extraction, sector flags, and checklist automation
- `services/bfsi_nbfc_service.py` for deterministic GNPA, NNPA, CRAR, ALM mismatch, PSL posture, ALM bucket extraction, sector flags, and checklist automation
- `GET /cases/{id}/tech-saas-metrics`, `GET /cases/{id}/manufacturing-metrics`, and `GET /cases/{id}/bfsi-nbfc-metrics`
- Workflow-integrated Phase 12 refresh so syntheses, reports, trace events, and CrewAI prompts consume the same structured sector-pack state
- `agents/phase12_tools.py` plus phase-aware prompt context so the coordinator and relevant workstreams can inspect structured sector outputs directly
- Dedicated Phase 12 evaluation coverage and five focused pytest cases for summary extraction, checklist updates, workflow integration, and CrewAI tool attachment

### What was ADDED in Phase 13
- `services/report_markdown.py` as the markdown block-parser layer for headings, lists, paragraphs, and tables
- `services/report_renderer.py` for Jinja2-based rich full-report and financial-annex rendering across `standard`, `lender`, `board_memo`, and `one_pager` templates
- `services/docx_service.py` for DOCX rendering with cover page, table of contents, section headings, lists, and markdown tables
- `services/pdf_service.py` for PDF rendering with the same markdown-first report structure
- `templates/*.md.j2` for standard, lender, board memo, one-pager, and financial-annex templates
- `GET /cases/{id}/reports/full-report` and `GET /cases/{id}/reports/financial-annex`
- report-bundle download support plus workflow-level persistence of report-template choice and binary artifact metadata
- export-package inclusion for full-report markdown, financial-annex markdown, DOCX, and PDF report artifacts
- workbench template selection and artifact download links on the run detail page
- Dedicated Phase 13 evaluation coverage and five focused pytest cases for rendering, artifact generation, workflow integration, and export integrity

### What was ADDED in Phase 14
- `source_adapters/base.py` plus six concrete India adapters for MCA21, GSTIN, SEBI SCORES, RoC filings, CIBIL stub, and sanctions/watchlist screening
- `services/source_adapter_service.py` as the registry-backed catalog and fetch orchestration layer
- `POST /cases/{id}/source-adapters/{adapter_id}/fetch` for connector-backed evidence ingestion
- richer `SourceAdapterSummary` metadata with status, credential requirements, fetch support, source kind, and default workstream details
- shared connector ingestion through the same dedup, storage, chunking, evidence extraction, and entity extraction path used by uploaded documents
- Dedicated Phase 14 evaluation coverage and five focused pytest cases for catalog exposure, fetch behavior, and downstream domain-engine consumption

### What was ADDED in Phase 7
- CrewAI multi-agent orchestration (`agents/` package) — 9 workstream agents + 1 coordinator
- Agent configs: India-focused domain experts with motion_pack/sector_pack context awareness
- Structured output: WorkstreamAnalysisOutput, ExecutiveSummaryOutput Pydantic models
- CaseContext builder: pre-loads all case data for crew kickoff
- Crew factory: builds Agent+Task per active workstream + coordinator summary task
- WorkflowService branching: CrewAI path when LLM configured, deterministic fallback otherwise
- 5 new settings: llm_provider, llm_api_key, llm_model, crew_verbose, crew_max_rpm
- Trace events: crew_initialized, agent_{workstream}, coordinator_synthesis
- Robust output parsing: structured pydantic extraction with raw text fallback

### What was ADDED in Phase 6
- Typed API client (`lib/api-client.ts`) — 15 mutation functions with auth headers
- Next.js API proxy via `rewrites` in `next.config.ts` (avoids CORS)
- 8 interactive client components: CreateCaseModal, CreateCaseButton, DocumentUpload, IssueManager, ChecklistPanel, RequestQaPanel, ApprovalPanel, RunWorkflowButton, LiveRunViewer
- Case creation modal with motion_pack/sector_pack selectors
- Drag-and-drop document upload with document_kind/source_kind/workstream_domain
- Inline issue status/severity editing + auto-scan button
- SVG coverage ring chart for checklist progress + inline status toggles
- Reviewer decision form with optional decision override
- SSE-connected LiveRunViewer for real-time trace event streaming
- All interactive components integrated into case workspace and run viewer pages

### What was ADDED in Phase 5
- pgvector embedding support: configurable provider (none/openai/local), raw float32 byte storage
- Hybrid search: keyword (BM25-like) + cosine similarity with 0.4/0.6 weighting
- Evidence conflict detection: duplicate (>0.98 similarity) and contradictory (>0.92 with different values)
- Alembic migration 002: vector column + HNSW index + GIN full-text index
- POST /cases/{id}/search and GET /cases/{id}/evidence/conflicts endpoints

### What was ADDED in Phase 4
- Semantic chunking engine (`ingestion/chunker.py`) — heading > paragraph > sentence splitting with char offsets and page detection
- Rule-based entity extractor (`ingestion/entity_extractor.py`) — financial metrics, legal entities, regulatory IDs, India identifiers (CIN, GSTIN)
- ChunkRecord ORM model linked to DocumentArtifactRecord (cascade delete, ready for Phase 5 embeddings)
- Upgraded PDF parser — table extraction via pdfplumber as markdown
- Upgraded DOCX parser — heading structure preservation + table extraction
- Upgraded XLSX parser — all sheets as markdown tables (up to 8 sheets, 200 rows)
- SHA256 document dedup — second upload of identical content is a no-op
- GET /documents/{doc_id}/chunks endpoint with pagination

### What was WIRED in Phase 3
- ~~Redis 7.4 — in Docker Compose, never connected~~ -- Redis pool wired in lifespan when background_mode=true; arq worker dispatches workflow jobs
- ~~Alembic 1.18.4 — no migrations directory~~ -- alembic.ini, async env.py, initial migration (14 tables)

### What was FIXED in Phase 1
- ~~pdfplumber and openpyxl imported but missing from pyproject.toml~~ -- added to dependencies
- ~~workflow_service.execute_run() has no error handling~~ -- try/except sets FAILED status + trace event
- ~~Issue heuristics use naive substring matching~~ -- now uses word-boundary regex
- ~~Health endpoint has hardcoded values~~ -- reads from configurable Settings
- ~~Approval has no manual decision override~~ -- optional decision field added
- ~~Storage service silently falls back to local~~ -- logger.warning on fallback
- ~~Parsers crash on corrupt files~~ -- all parsers wrapped in try/except

### What was ADDED in Phase 2
- ~~No PATCH endpoints~~ -- PATCH for cases, issues, evidence, requests, Q&A
- ~~No DELETE endpoints~~ -- DELETE for cases (cascade), documents, issues
- ~~No individual GET endpoints~~ -- GET for documents/{id}, evidence/{id}, issues/{id}
- ~~No pagination~~ -- skip/limit on list_cases
- ~~No download endpoint~~ -- GET .../export-packages/{id}/download streams ZIP

### What is MISSING
- No structured logging, tracing, or metrics
- No JWT authentication
- No multi-tenancy
- CrewAI agents wired with scoped read-only tools, but they still require LLM_PROVIDER + LLM_API_KEY to activate
- Real-time tool and step streaming is still not implemented; trace events are persisted after crew completion
- No dedicated financial summary panel in the Next.js case workspace yet; Phase 8 is currently exposed through the API, workflow output, and reports rather than a bespoke UI view
- No dedicated legal/tax/regulatory analyst panels in the Next.js workspace yet; Phase 9 is currently exposed through APIs, workflow outputs, and evaluation surfaces rather than bespoke UI views
- No dedicated commercial/operations/cyber/forensic analyst panels in the Next.js workspace yet; Phase 10 is currently exposed through APIs, workflow outputs, and evaluation surfaces rather than bespoke UI views
- No dedicated motion-pack analyst panels yet for valuation bridges, borrower scorecards, or vendor tiering; Phase 11 is currently exposed through APIs, workflow outputs, reports, and evaluation surfaces rather than bespoke UI views
- No dedicated sector-pack analyst panels yet for Tech/SaaS, Manufacturing, or BFSI/NBFC detail; Phase 12 is currently exposed through APIs, workflow outputs, reports, and evaluation surfaces rather than bespoke UI views
- No WYSIWYG report editor or brand-theming system yet; Phase 13 currently provides deterministic template-based reporting and download flows rather than analyst-authored document composition
- No live premium connector credentials are wired by default; Phase 14 ships stub-capable production-structured adapters, but real provider access still depends on environment-specific base URLs, API keys, and feed permissions

## Layers

### Layer 1: API Control Plane (`apps/api/`)

```
apps/api/src/crewai_enterprise_pipeline_api/
  main.py              # App factory, lifespan (Redis pool), middleware
  worker.py            # arq WorkerSettings + run_workflow_job background task
  config.py            # pydantic-settings based configuration
  agents/
    __init__.py
    config.py          # 9 workstream agent configs + coordinator + pack context helpers
    models.py          # WorkstreamAnalysisOutput, ExecutiveSummaryOutput
    crew.py            # CaseContext, compact prompt snapshots, crew factory, run_crew async wrapper
    compliance_tools.py # Structured legal/tax/regulatory lookup tools for CrewAI
    financial_tools.py # Structured financial ratio and sector benchmark tools for CrewAI
    phase10_tools.py   # Structured commercial/operations/cyber/forensic lookup tools for CrewAI
    phase11_tools.py   # Structured buy-side, credit, and vendor motion-pack review tools for CrewAI
    phase12_tools.py   # Structured Tech/SaaS, Manufacturing, and BFSI/NBFC lookup tools for CrewAI
    packs/             # Motion-pack specialist prompts/configs for buy-side, credit, and vendor flows
    tools.py           # Scoped read-only CrewAI tools over pre-loaded evidence, issues, checklist, chunks, and phase-specific summaries
  api/
    router.py          # Mounts /system, /source-adapters, /cases under /api/v1/
    security.py        # Header-based RBAC (X-CEP-User-{Id,Name,Email,Role})
    routes/
      health.py        # GET /health, /readiness, /overview
      cases.py         # All case CRUD + sub-resource endpoints
      source_adapters.py  # GET /source-adapters (read-only catalog)
  domain/
    models.py          # 113 Pydantic schemas and StrEnums
  db/
    base.py            # UUID generation, TimestampedMixin
    models.py          # 14 SQLAlchemy ORM models (CaseRecord is aggregate root, ChunkRecord for embeddings)
    session.py         # AsyncSession factory
  services/
    case_service.py        # Case CRUD + sub-resource operations
    ingestion_service.py   # Document upload, parse, chunk, evidence extract
    checklist_service.py   # Template seeding, coverage summaries
    issue_service.py       # Heuristic-based issue scanning
    approval_service.py    # Review decision logic
    workflow_service.py    # Orchestrates runs (CrewAI when LLM configured, deterministic fallback)
    synthesis_service.py   # Workstream synthesis (deterministic template fill)
    report_service.py      # Executive memo + rich report context generation
    report_renderer.py     # Jinja2 rich-report rendering service
    report_markdown.py     # Markdown block parsing helpers for DOCX/PDF renderers
    docx_service.py        # DOCX rendering from markdown
    pdf_service.py         # PDF rendering from markdown
    document_signal_utils.py  # Shared artifact text snapshots for Phase 9 signal extraction
    financial_qoe_service.py  # Phase 8 QoE summary, ratios, flags, checklist automation
    legal_service.py          # Phase 9 legal structure and contract-clause analysis
    tax_service.py            # Phase 9 tax compliance summary and checklist automation
    regulatory_service.py     # Phase 9 compliance matrix generation and checklist automation
    commercial_service.py     # Phase 10 commercial concentration and retention analysis
    operations_service.py     # Phase 10 dependency and supply-continuity analysis
    cyber_service.py          # Phase 10 cyber/privacy control and incident analysis
    forensic_service.py       # Phase 10 forensic flag detection and checklist automation
    checklist_catalog.py   # Centralized motion-pack + sector-pack checklist definitions
    buy_side_service.py    # Phase 11 buy-side valuation bridge, SPA, and PMI analysis
    credit_service.py      # Phase 11 borrower scorecard and covenant-tracking analysis
    vendor_service.py      # Phase 11 vendor risk-tiering and questionnaire analysis
    sector_signal_utils.py # Shared sector-pack extraction helpers for metrics and status phrases
    tech_saas_service.py   # Phase 12 Tech/SaaS ARR, retention, and unit-economics analysis
    manufacturing_service.py # Phase 12 manufacturing plant, working-capital, and asset-register analysis
    bfsi_nbfc_service.py   # Phase 12 BFSI/NBFC asset-quality, capital, liquidity, and PSL analysis
    embedding_service.py   # Vector embedding generation (none/openai/local providers)
    export_service.py      # ZIP export package creation
    search_service.py      # Hybrid BM25+cosine search, evidence conflict detection
    source_adapter_service.py # Adapter catalog and fetch orchestration
  ingestion/
    parsers.py         # PDF (tables), DOCX (headings+tables), XLSX (multi-sheet), CSV, JSON, TXT
    financial_parser.py # Structured financial workbook parser for QoE metrics and adjustments
    chunker.py         # Semantic chunking: heading > paragraph > sentence (1200 char max)
    entity_extractor.py  # Rule-based: financial, legal, regulatory, India IDs (CIN, GSTIN)
  storage/
    service.py         # S3/MinIO with local fallback
  source_adapters/
    base.py            # Shared adapter contract, stub/live dispatch, HTTP helpers
    mca21.py           # MCA21 company master-data connector
    gstin.py           # GSTIN registration and filing connector
    sebi_scores.py     # SEBI SCORES complaints/disclosure connector
    roc.py             # Registrar of Companies filings connector
    cibil.py           # CIBIL stub connector
    sanctions.py       # Sanctions / debarment screening connector
  evaluation/
    runner.py          # CLI: python -m ...evaluation.runner --suite <name>
    harness.py         # Test infrastructure (isolated SQLite per run)
    scenarios.py       # 22 scenarios across 12 suites
```

### Layer 2: Web Workbench (`apps/web/`)

```
apps/web/src/
  app/
    page.tsx                          # Dashboard with CreateCaseButton
    layout.tsx                        # Root layout
    cases/[caseId]/page.tsx           # Case workspace (fully interactive)
    cases/[caseId]/runs/[runId]/page.tsx  # Run viewer with live SSE stream
  lib/
    workbench-data.ts                 # API client (GET) + 480 lines demo fallback
    api-client.ts                     # Typed mutation client (15 functions, POST/PATCH/DELETE)
  components/
    CreateCaseModal.tsx               # Case creation modal form
    CreateCaseButton.tsx              # State wrapper for modal toggle
    DocumentUpload.tsx                # Drag-and-drop file upload
    IssueManager.tsx                  # Inline issue editor + auto-scan
    ChecklistPanel.tsx                # SVG coverage ring + status toggles
    RequestQaPanel.tsx                # Request + Q&A inline editing
    ApprovalPanel.tsx                 # Reviewer decision form
    RunWorkflowButton.tsx             # Workflow trigger + export
    LiveRunViewer.tsx                 # SSE real-time event stream
    interactive.module.css            # Styles for all interactive components
```

- Next.js 16 App Router, server components (pages) + client components (interactions)
- Pure CSS modules (no Tailwind)
- Full CRUD mutations via typed API client through Next.js proxy
- SSE live streaming for real-time run trace events
- Falls back to hardcoded demo data when API unreachable (GET only)

### Layer 3: Infrastructure

- **PostgreSQL 17** (:5432) — primary datastore
- **Redis 7.4** (:6379) — arq job queue when background_mode=true
- **MinIO** (:9000 API, :9001 console) — S3-compatible object storage
- All managed via `docker-compose.yml` with health checks and named volumes

## Pack Model

Motion Packs x Sector Packs x India Rule Packs. Any combination is valid.

**Motion Packs:** buy_side_diligence, credit_lending, vendor_onboarding
**Sector Packs:** tech_saas_services, manufacturing_industrials, bfsi_nbfc
**India Rule Packs:** MCA, SEBI, RBI/FEMA/FDI, CCI, GST, Labour, Privacy (DPDP 2025)

## Data Flow (7 Steps)

1. `POST /cases` — Create case with motion_pack + sector_pack
2. `POST /cases/{id}/checklist/seed` — Seed checklist from pack templates
3. `POST /cases/{id}/documents/upload` — Parse, chunk, extract evidence
3a. `POST /cases/{id}/source-adapters/{adapter_id}/fetch` — Fetch connector data and ingest it as a first-class artifact
4. `POST /cases/{id}/issues/scan` — Heuristic issue flagging
5. `POST /cases/{id}/approvals/review` — Reviewer gate
6. `POST /cases/{id}/runs` — Execute workflow run (traces + syntheses + reports)
7. `POST /cases/{id}/runs/{rid}/export-package` — Generate ZIP export

## Key Conventions

- ORM classes end in `Record` (CaseRecord, EvidenceNodeRecord)
- Service classes end in `Service` (CaseService, WorkflowService)
- Pydantic schemas: `*Create` (input), `*Summary` (list), `*Detail` (full), `*Result` (action)
- All domain enums + Pydantic schemas in `domain/models.py`
- All ORM models in `db/models.py`
- All DB/storage I/O is async/await
- Services compose via constructor injection, not inheritance

## Target Architecture

See `docs/MASTERPLAN.docx` for the 18-phase plan to reach full production state:
- Real CrewAI multi-agent orchestration with 9 domain agents
- pgvector hybrid search for evidence intelligence
- Interactive frontend with full CRUD + live SSE streaming
- Deep domain engines (Financial QoE, Legal/Tax/Regulatory, Commercial/Forensic)
- Additional Phase 15+ roadmap depth from `MASTERPLAN.docx` beyond the now-complete Phase 14 connector tranche
- Enterprise Security (JWT + Multi-tenancy + Audit)
- JWT auth, multi-tenancy, audit logging
- OpenTelemetry + Prometheus observability
- Production Docker images with deployment runbook
