# CLAUDE.md

## Current State

**Completed phases:** 0-14 | **Next:** Phase 15
**Tests:** 120 pytest, 22 eval scenarios (12 suites) | **Blockers:** None

## Project Overview

India-focused due diligence system: FastAPI API (`apps/api/`) + Next.js workbench (`apps/web/`).
Pack model: `motion_packs x sector_packs x India rule_packs`.
CrewAI is wired through Phase 7 and activates only when `LLM_PROVIDER` + `LLM_API_KEY` are set. A post-Phase-7 enhancement added scoped read-only evidence, issue, and checklist tools over pre-loaded case snapshots, and canonical Phase 8 is now complete with a Financial Quality of Earnings (QoE) engine: structured workbook parsing, normalized EBITDA adjustments, ratio analysis, financial flags, workflow integration, and checklist auto-satisfaction. Deterministic fallback remains the default safety path (AD-001, AD-027, AD-030).
Canonical Phase 9 is now complete with a Legal / Tax / Regulatory engine: structured legal summaries, contract clause review, DIN and shareholding extraction, tax compliance summaries, BFSI-aware compliance matrix generation, checklist auto-satisfaction, workflow refresh, report integration, CrewAI compliance tools, and a dedicated Phase 9 evaluation suite (AD-036 to AD-038).
Canonical Phase 10 is now complete with Commercial / Operations / Cyber / Forensic engines: structured customer concentration and retention analysis, operations dependency and supplier-concentration analysis, DPDP/security control review with analyst-readable flagging, forensic flag detection, checklist automation, workflow/report integration, CrewAI Phase 10 tools, and a dedicated Phase 10 evaluation suite (AD-039 to AD-042).
Canonical Phase 11 is now complete with Motion Pack Deepening: centralized motion-pack checklist composition, structured buy-side analysis, borrower scorecards, vendor risk tiering, motion-pack checklist auto-satisfaction, workflow/report/synthesis integration, CrewAI motion-pack specialist tools and prompts, and a dedicated Phase 11 evaluation suite (AD-043).
Canonical Phase 12 is now complete with Sector Pack Deepening: deterministic Tech/SaaS ARR-waterfall and unit-economics metrics, Manufacturing capacity and asset-register analysis, BFSI/NBFC asset-quality and ALM analysis, sector-pack checklist auto-satisfaction, workflow/report/synthesis integration, CrewAI Phase 12 tools and snapshots, and a dedicated Phase 12 evaluation suite (AD-044 to AD-045).
Canonical Phase 13 is now complete with Rich Reporting + DOCX/PDF Export: Jinja2-driven report templates for standard, lender, board memo, and one-pager outputs; markdown-first full-report and financial-annex rendering; binary DOCX and PDF generation; workflow-level report-template persistence; bundle download endpoints; export-package inclusion of DOCX/PDF artifacts; updated workbench template selection; and a dedicated Phase 13 evaluation suite (AD-046 to AD-047).
Canonical Phase 14 is now complete with India Data Connectors: a registered connector framework for MCA21, GSTIN, SEBI SCORES, RoC filings, CIBIL stub, and sanctions/watchlist screening; shared connector-to-artifact ingestion through the same storage, chunking, and evidence pipeline used by uploads; source-adapter fetch endpoints with availability/stub metadata; and a dedicated Phase 14 evaluation suite (AD-048 to AD-049).

## Execution Contract For This Repo

- Use `docs/MASTERPLAN.docx` as the strategic roadmap when available. Treat `docs/MASTERPLAN.pdf` as the presentation/export companion.
- Use the actual repo code, tests, scripts, and verified command outputs as the execution truth.
- Complete one master-plan phase at a time unless the user explicitly asks for batching.
- Do not call a phase complete if it is still a prototype, partial slice, or happy-path-only implementation.
- After each completed phase, update this file plus `docs/HANDOFF.md`, `docs/PROGRESS.md`, `docs/DECISIONS.md`, and `docs/architecture.md`.

## Resume Read Order

When resuming this repo in a new session, read in this order:

1. `CLAUDE.md`
2. `docs/HANDOFF.md`
3. `docs/PROGRESS.md`
4. `docs/DECISIONS.md`
5. `docs/architecture.md`
6. `docs/verification.md`
7. the relevant part of `docs/MASTERPLAN.docx` (preferred) or `docs/MASTERPLAN.pdf`

If docs disagree with the code, trust the code/tests/runtime outputs for the current state and then repair the docs.

## Commands

```powershell
# Full verification gate (run before closing a phase)
./scripts/check.ps1

# Individual backend checks
cd apps/api && python -m ruff check src tests && python -m pytest

# Individual web checks
cd apps/web && npm run lint && npm run typecheck

# Evaluation suites
cd apps/api && python -m crewai_enterprise_pipeline_api.evaluation.runner
cd apps/api && python -m crewai_enterprise_pipeline_api.evaluation.runner --suite <name>

# Dev servers
./scripts/dev-stack.ps1    # Docker: Postgres, Redis, MinIO
./scripts/dev-api.ps1      # FastAPI :8000
./scripts/dev-web.ps1      # Next.js :3000
./scripts/dev-worker.ps1   # arq worker
```

## Do Not Rename

- Enum values in `domain/models.py`
- Checklist `template_key` values in `checklist_service.py`
- `ReportBundleKind` strings
- Auth header names (`X-CEP-User-*`)
- Export bundle path mappings in `export_service.py`

## Key Conventions

- ORM: `*Record`, Services: `*Service`, Pydantic: `*Create/*Summary/*Detail/*Result/*Update`
- All domain enums + Pydantic models live in `domain/models.py`, ORM lives in `db/models.py`
- All DB/storage I/O is async/await, services compose via constructor injection
- Tests: SQLite (`aiosqlite`), evaluation harness is the primary quality gate
- Frontend: CSS modules only (no Tailwind), Next.js 16 App Router

## Reference Docs

- `docs/HANDOFF.md` - session recovery checkpoint
- `docs/PROGRESS.md` - completion history per phase
- `docs/DECISIONS.md` - architecture rationale (AD-001 onward)
- `docs/architecture.md` - file layout, component inventory, honest current-state assessment
- `docs/MASTERPLAN.docx` - canonical machine-readable 18-phase blueprint
- `docs/MASTERPLAN.pdf` - visual/export companion to the master plan

## After Every Phase

Update:

- `CLAUDE.md`
- `docs/HANDOFF.md`
- `docs/PROGRESS.md`
- `docs/DECISIONS.md`
- `docs/architecture.md`

Keep this file's **Current State** section accurate.
