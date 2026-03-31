# CLAUDE.md

## Current State

**Completed phases:** 0–7 | **Next:** Phase 8
**Tests:** 83 pytest, 11 eval scenarios (5 suites) | **Blockers:** None

## Project Overview

India-focused due diligence system: FastAPI API (`apps/api/`) + Next.js workbench (`apps/web/`).
Pack model: motion_packs × sector_packs × India rule_packs.
CrewAI wired in Phase 7 — activates when LLM_PROVIDER + LLM_API_KEY are set; deterministic fallback otherwise (AD-001).

## Commands

```powershell
# Full verification gate (run before commit)
./scripts/check.ps1

# Individual
cd apps/api && python -m ruff check src tests && python -m pytest
cd apps/web && npm run lint && npm run typecheck

# Eval suites
cd apps/api && python -m crewai_enterprise_pipeline_api.evaluation.runner
cd apps/api && python -m crewai_enterprise_pipeline_api.evaluation.runner --suite <name>

# Dev servers
./scripts/dev-stack.ps1    # Docker: Postgres, Redis, MinIO
./scripts/dev-api.ps1      # FastAPI :8000
./scripts/dev-web.ps1      # Next.js :3000
./scripts/dev-worker.ps1   # arq worker
```

## Do Not Rename (coupled across tests, eval, UI, smoke)

- Enum values in `domain/models.py`
- Checklist `template_key` values in `checklist_service.py`
- `ReportBundleKind` strings
- Auth header names (`X-CEP-User-*`)
- Export bundle path mappings in `export_service.py`

## Key Conventions

- ORM: `*Record`, Services: `*Service`, Pydantic: `*Create/*Summary/*Detail/*Result/*Update`
- All domain enums + Pydantic in `domain/models.py`, ORM in `db/models.py`
- All DB/storage I/O is async/await, services compose via constructor injection
- Tests: SQLite (aiosqlite), eval harness is the primary quality gate
- Frontend: CSS modules only (no Tailwind), Next.js 16 App Router

## Reference Docs (read ONLY when needed for current task)

- `docs/HANDOFF.md` — session recovery checkpoint
- `docs/PROGRESS.md` — completion history per phase
- `docs/DECISIONS.md` — architecture rationale (AD-001 through AD-027)
- `docs/architecture.md` — file layout, component inventory, what's real vs missing
- `docs/MASTERPLAN.pdf` — 18-phase blueprint (read specific pages when starting a new phase)

## After Every Phase

Update: HANDOFF.md, PROGRESS.md, DECISIONS.md, architecture.md. Keep this file's "Current State" section current.
