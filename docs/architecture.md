# Architecture Overview

> **Last updated:** 2026-03-30 (Phase 5 -- Evidence Intelligence)
> **Update rule:** This file is updated after every masterplan phase to reflect actual system state.

## System Summary

India-focused due diligence operating system: FastAPI control plane + Next.js analyst workbench.
Manages diligence cases, document ingestion, evidence extraction, issue flags, checklist coverage,
reviewer approvals, workflow runs, report bundles, and durable ZIP export packages.

## Architecture Diagram

See `docs/MASTERPLAN.pdf` pages 3-8 for full diagrams including:
- System architecture (all components and connections)
- 7-step data flow pipeline
- Phase dependency graph
- CrewAI multi-agent architecture (target state)
- Pack model matrix
- Database ER diagram

## Current State (Honest Assessment)

### What is REAL and WORKING
- 15 SQLAlchemy ORM models with proper relationships, cascades, timestamps
- 103 Pydantic schemas with consistent naming conventions
- 11 service classes (functional but 100% deterministic — no AI)
- 41 REST endpoints (full CRUD + SSE streaming + chunks + search + conflicts)
- Document parsing for 6 formats (PDF with tables, DOCX with headings+tables, XLSX multi-sheet, CSV, JSON, TXT)
- Semantic chunking engine (heading > paragraph > sentence splitting, 1200 char max)
- Rule-based entity extraction (financial, legal, regulatory, India identifiers)
- SHA256 document dedup (same content returns existing artifact)
- Header-based RBAC with 4 roles (VIEWER, ANALYST, REVIEWER, ADMIN)
- Evaluation harness with 5 suites, 11 scenarios
- 71 pytest unit tests
- Export ZIP packages (markdown only)
- Docker Compose stack (PostgreSQL 17, Redis 7.4, MinIO)

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

### What is DECLARED BUT NOT WIRED
- **CrewAI 1.12.2** — in pyproject.toml, zero `import crewai` in any src/ file
- **httpx 0.28.1** — in pyproject.toml, never imported in src/

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
- Frontend is 100% read-only (zero POST/PATCH/DELETE from web)
- No structured logging, tracing, or metrics
- No JWT authentication
- No multi-tenancy

## Layers

### Layer 1: API Control Plane (`apps/api/`)

```
apps/api/src/crewai_enterprise_pipeline_api/
  main.py              # App factory, lifespan (Redis pool), middleware
  worker.py            # arq WorkerSettings + run_workflow_job background task
  config.py            # pydantic-settings based configuration
  api/
    router.py          # Mounts /system, /source-adapters, /cases under /api/v1/
    security.py        # Header-based RBAC (X-CEP-User-{Id,Name,Email,Role})
    routes/
      health.py        # GET /health, /readiness, /overview
      cases.py         # All case CRUD + sub-resource endpoints
      source_adapters.py  # GET /source-adapters (read-only catalog)
  domain/
    models.py          # ~96 Pydantic schemas + all StrEnums
  db/
    base.py            # UUID generation, TimestampedMixin
    models.py          # 15 SQLAlchemy ORM models (CaseRecord is aggregate root, ChunkRecord for embeddings)
    session.py         # AsyncSession factory
  services/
    case_service.py        # Case CRUD + sub-resource operations
    ingestion_service.py   # Document upload, parse, chunk, evidence extract
    checklist_service.py   # Template seeding, coverage summaries
    issue_service.py       # Heuristic-based issue scanning
    approval_service.py    # Review decision logic
    workflow_service.py    # Orchestrates runs (deterministic, no CrewAI)
    synthesis_service.py   # Workstream synthesis (deterministic template fill)
    report_service.py      # Executive memo generation
    embedding_service.py   # Vector embedding generation (none/openai/local providers)
    export_service.py      # ZIP export package creation
    search_service.py      # Hybrid BM25+cosine search, evidence conflict detection
  ingestion/
    parsers.py         # PDF (tables), DOCX (headings+tables), XLSX (multi-sheet), CSV, JSON, TXT
    chunker.py         # Semantic chunking: heading > paragraph > sentence (1200 char max)
    entity_extractor.py  # Rule-based: financial, legal, regulatory, India IDs (CIN, GSTIN)
  storage/
    service.py         # S3/MinIO with local fallback
  evaluation/
    runner.py          # CLI: python -m ...evaluation.runner --suite <name>
    harness.py         # Test infrastructure (isolated SQLite per run)
    scenarios.py       # 11 scenarios across 5 suites
```

### Layer 2: Web Workbench (`apps/web/`)

```
apps/web/src/
  app/
    page.tsx                          # Dashboard (read-only)
    layout.tsx                        # Root layout
    cases/[caseId]/page.tsx           # Case workspace (read-only)
    cases/[caseId]/runs/[runId]/page.tsx  # Run viewer (read-only)
  lib/
    workbench-data.ts                 # API client (GET only) + 480 lines demo fallback
```

- Next.js 16 App Router, server components only
- Pure CSS modules (no Tailwind)
- Zero mutations — completely read-only
- Falls back to hardcoded demo data when API unreachable (silently hides failures)

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

See `docs/MASTERPLAN.pdf` for the 18-phase plan to reach full production state:
- Real CrewAI multi-agent orchestration with 9 domain agents
- pgvector hybrid search for evidence intelligence
- Interactive frontend with full CRUD + live SSE streaming
- Deep domain engines (Financial QoE, Legal/Tax/Regulatory, Commercial/Forensic)
- India data connectors (MCA21, GSTIN, SEBI, CIBIL, sanctions)
- JWT auth, multi-tenancy, audit logging
- Rich DOCX/PDF reporting
- OpenTelemetry + Prometheus observability
- Production Docker images with deployment runbook
