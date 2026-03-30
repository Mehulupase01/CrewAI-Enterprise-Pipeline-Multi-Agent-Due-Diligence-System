# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Session Startup (READ THESE FIRST)

On every new session or context reset, read these files before doing anything else:

1. **`docs/HANDOFF.md`** -- Where we left off, what to do next, mid-phase checkpoint
2. **`docs/PROGRESS.md`** -- Which phases are complete, detailed history
3. **`docs/DECISIONS.md`** -- Architecture decisions and rationale (the WHY)
4. **`docs/architecture.md`** -- Honest current system state (the NOW)
5. **`docs/MASTERPLAN.pdf`** -- Full 18-phase implementation blueprint (the PLAN)

After every phase completion, update ALL of the above plus this file. See `docs/HANDOFF.md` for the exact checklist. This is non-negotiable -- it is how project context survives across sessions.

## Project Overview

India-focused due diligence operating system: FastAPI control plane (`apps/api/`) + Next.js analyst workbench (`apps/web/`). Manages diligence cases, document ingestion, evidence extraction, issue flags, checklist coverage, reviewer approvals, workflow runs, report bundles, and durable ZIP export packages.

Uses a **pack model**: motion packs (buy_side_diligence, credit_lending, vendor_onboarding) x sector packs (tech_saas_services, manufacturing_industrials, bfsi_nbfc) x India rule packs (MCA, SEBI, RBI, CCI, GST, labour, privacy).

**Current state:** Phase 4 (Document Intelligence) complete. Full CRUD API with async background processing, semantic document intelligence: heading-aware chunking engine, rule-based entity extraction (financial, legal, regulatory, India identifiers), upgraded parsers (PDF tables, DOCX headings+tables, XLSX multi-sheet), SHA256 document dedup, chunks endpoint. arq worker dispatches workflow runs via Redis when `background_mode=true`, falls back to synchronous execution otherwise. Alembic migrations created (initial schema with 15 tables including ChunkRecord). SSE stream endpoint for real-time run progress. CrewAI is installed but NOT wired into runtime -- `workflow_service.py` is fully deterministic.

## Commands

```powershell
# Setup (one-time)
./scripts/bootstrap.ps1                          # Install Python + npm deps in Conda env

# Local stack
./scripts/dev-stack.ps1                          # Docker: Postgres 17, Redis 7.4, MinIO
./scripts/dev-api.ps1                            # FastAPI on :8000 with hot-reload
./scripts/dev-web.ps1                            # Next.js on :3000
./scripts/dev-worker.ps1                         # arq background worker

# Full verification gate
./scripts/check.ps1                              # ruff + pytest + evaluation + npm lint + typecheck

# Individual checks (from apps/api/)
python -m ruff check src tests                   # Lint
python -m pytest                                 # All tests (60 tests)
python -m pytest tests/test_cases.py -k "test_name"  # Single test

# Individual checks (from apps/web/)
npm run lint                                     # ESLint
npm run typecheck                                # TypeScript strict check

# Evaluation suites
./scripts/evaluate.ps1                           # All suites (11 scenarios)
./scripts/evaluate.ps1 -Suite phase5_first_slice
./scripts/evaluate.ps1 -Suite credit_lending_expansion
./scripts/evaluate.ps1 -Suite vendor_onboarding_expansion
./scripts/evaluate.ps1 -Suite manufacturing_industrials_expansion
./scripts/evaluate.ps1 -Suite bfsi_nbfc_expansion

# Live smoke test (requires running stack)
./scripts/smoke.ps1
```

Direct API run: `uvicorn crewai_enterprise_pipeline_api.main:app --host 0.0.0.0 --port 8000 --reload`

## Architecture

### API (`apps/api/src/crewai_enterprise_pipeline_api/`)

Layered async: **Routes -> Services -> DB/Storage**

- **`main.py`** -- App factory with lifespan. Auto-creates schema, wires Redis pool (when background_mode=true), adds `X-Request-ID` middleware.
- **`worker.py`** -- arq WorkerSettings + `run_workflow_job` background task. Run with: `arq crewai_enterprise_pipeline_api.worker.WorkerSettings`.
- **`api/router.py`** -- Mounts `/system`, `/source-adapters`, `/cases` under `/api/v1/`.
- **`api/security.py`** -- Header-based RBAC (`X-CEP-User-{Id,Name,Email,Role}`). Three tiers: read (VIEWER+), write (ANALYST+), reviewer (REVIEWER+). Auth bypassed when `APP_ENV` is development/test.
- **`domain/models.py`** -- ~98 Pydantic schemas/enums. Naming: `*Create`, `*Summary`, `*Detail`, `*Result`. Key enums: `MotionPack`, `SectorPack`, `WorkstreamDomain`, `FlagSeverity`.
- **`db/models.py`** -- 15 SQLAlchemy ORM models. `CaseRecord` is aggregate root with cascade deletes. `ChunkRecord` linked to `DocumentArtifactRecord` (ready for Phase 5 embeddings). Classes end in `Record`. UUIDs from `db/base.py`, UTC timestamps via `TimestampedMixin`.
- **`services/`** -- Services compose sub-services via constructor (not inheritance). `WorkflowService` orchestrates runs by delegating to `CaseService`, `ChecklistService`, `ReportService`, `SynthesisService`.
- **`ingestion/parsers.py`** -- Parses PDF (with table extraction), DOCX (heading structure + tables), XLSX (multi-sheet markdown tables), CSV, JSON, TXT. All parsers wrapped in try/except for graceful failure on corrupt files.
- **`ingestion/chunker.py`** -- Semantic chunking engine: heading > paragraph > sentence splitting. 1200-char max. Carries section_title, page_number, char_start, char_end.
- **`ingestion/entity_extractor.py`** -- Rule-based extraction: financial (revenue, EBITDA, PAT, debt, auditor, opinion), legal (parties, dates, governing law), regulatory (reg numbers, validity), India IDs (CIN, GSTIN). Returns `EvidenceItemCreate` instances.
- **`storage/service.py`** -- S3/MinIO with local fallback. Path: `cases/{case_id}/artifacts/{artifact_id}/{filename}`. SHA256 on every store.
- **`evaluation/`** -- Scenario-based integration harness (not pytest). Runs full HTTP flows against isolated SQLite. Outputs JSON scorecards to `artifacts/evaluations/`.

### Web (`apps/web/`)

Next.js 16 App Router, server components only. No client-side state management.

- **Routes:** `/` (dashboard), `/cases/[caseId]` (workspace), `/cases/[caseId]/runs/[runId]` (run viewer).
- **`src/lib/workbench-data.ts`** -- API client with `cache: "no-store"`. Falls back to built-in demo data when API unreachable (can silently hide backend failures). No auth headers sent.
- **Styling:** Pure CSS modules, no Tailwind. Path alias `@/*` -> `./src/*`.

### Data flow

1. `POST /cases` -> 2. `POST /cases/{id}/checklist/seed` -> 3. `POST /cases/{id}/documents/upload` (parse + chunk + evidence) -> 4. `POST /cases/{id}/issues/scan` (heuristic flags) -> 5. `POST /cases/{id}/approvals/review` (gate) -> 6. `POST /cases/{id}/runs` (traces + syntheses + reports) -> 7. `POST /cases/{id}/runs/{rid}/export-package` (ZIP)

## Infrastructure

Docker Compose: **PostgreSQL 17** (:5432, `crewai_pipeline`/`crewai`/`crewai`), **Redis 7.4** (:6379), **MinIO** (:9000 API, :9001 console, `minioadmin`/`minioadmin`). All with healthchecks and named volumes.

## Do Not Rename

These are coupled across tests, evaluation fixtures, UI, and smoke checks:
- Enum values in `domain/models.py` (MotionPack, SectorPack, WorkstreamDomain, etc.)
- Checklist `template_key` values in `checklist_service.py` (e.g., `financial_qoe.audited_financials`)
- `ReportBundleKind` strings
- Auth header names (`X-CEP-User-*`) in `security.py`
- Export bundle path mappings in `export_service.py`

## Known Gaps

- Web fetch layer sends no auth headers; silently falls back to demo data on API errors
- `scripts/bootstrap.ps1` hardcodes `C:\Users\Mehul-PC\anaconda3\Scripts\conda.exe`
- No frontend tests, no Playwright, no load tests
- arq 0.27 requires redis<6; Python redis client is 5.x while Docker runs Redis 7.4 server (wire-compatible)
