# CLAUDE.md

## Session Startup

Read **`docs/HANDOFF.md`** first. It has current state, what to do next, and blockers.
Read other docs **only when needed** for the current task:
- `docs/PROGRESS.md` -- completion history (read when you need phase details)
- `docs/DECISIONS.md` -- architecture rationale (read when making design choices)
- `docs/architecture.md` -- system state (read when you need file layout or component details)
- `docs/MASTERPLAN.pdf` -- 18-phase blueprint (read specific pages when starting a new phase)

After every phase completion, update: HANDOFF.md, PROGRESS.md, DECISIONS.md, architecture.md, and this file.

## Project Overview

India-focused due diligence system: FastAPI API (`apps/api/`) + Next.js workbench (`apps/web/`).
Pack model: motion_packs x sector_packs x India rule_packs. CrewAI installed but NOT wired.

## Commands

```powershell
./scripts/check.ps1                              # Full gate: ruff + pytest + eval + npm lint + typecheck
./scripts/dev-stack.ps1                          # Docker: Postgres, Redis, MinIO
./scripts/dev-api.ps1                            # FastAPI :8000
./scripts/dev-web.ps1                            # Next.js :3000
./scripts/dev-worker.ps1                         # arq worker
./scripts/evaluate.ps1                           # All eval suites (11 scenarios)
./scripts/evaluate.ps1 -Suite <suite_name>       # Single suite

# From apps/api/
python -m ruff check src tests
python -m pytest
python -m pytest tests/<file>.py -k "test_name"

# From apps/web/
npm run lint && npm run typecheck
```

## Do Not Rename

Coupled across tests, eval fixtures, UI, and smoke checks:
- Enum values in `domain/models.py`
- Checklist `template_key` values in `checklist_service.py`
- `ReportBundleKind` strings
- Auth header names (`X-CEP-User-*`)
- Export bundle path mappings in `export_service.py`

## Key Conventions

- ORM classes end in `Record`, services in `Service`
- Pydantic: `*Create`, `*Summary`, `*Detail`, `*Result`, `*Update`
- All domain enums + Pydantic in `domain/models.py`, ORM in `db/models.py`
- All DB/storage I/O is async/await
- Services compose via constructor injection
- Tests: SQLite (aiosqlite), eval harness is the primary quality gate
- CSS modules only (no Tailwind)
