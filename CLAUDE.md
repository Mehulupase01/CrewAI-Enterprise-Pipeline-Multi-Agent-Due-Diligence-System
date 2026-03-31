# CLAUDE.md

## Current State

**Completed phases:** 0-9 | **Next:** Phase 10
**Tests:** 97 pytest, 13 eval scenarios (7 suites) | **Blockers:** None

## Project Overview

India-focused due diligence system: FastAPI API (`apps/api/`) + Next.js workbench (`apps/web/`).
Pack model: `motion_packs x sector_packs x India rule_packs`.
CrewAI is wired through Phase 7 and activates only when `LLM_PROVIDER` + `LLM_API_KEY` are set. A post-Phase-7 enhancement added scoped read-only evidence, issue, and checklist tools over pre-loaded case snapshots, and canonical Phase 8 is now complete with a Financial Quality of Earnings (QoE) engine: structured workbook parsing, normalized EBITDA adjustments, ratio analysis, financial flags, workflow integration, and checklist auto-satisfaction. Deterministic fallback remains the default safety path (AD-001, AD-027, AD-030).
Canonical Phase 9 is now complete with a Legal / Tax / Regulatory engine: structured legal summaries, contract clause review, DIN and shareholding extraction, tax compliance summaries, BFSI-aware compliance matrix generation, checklist auto-satisfaction, workflow refresh, report integration, CrewAI compliance tools, and a dedicated Phase 9 evaluation suite (AD-036 to AD-038).

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
