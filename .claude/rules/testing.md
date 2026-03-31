---
description: Testing conventions (loaded only when editing test/eval files)
paths: ["apps/api/tests/**/*.py", "apps/api/src/**/evaluation/**/*.py"]
---

## pytest (`apps/api/tests/`)

- `python -m pytest` from `apps/api/`. TestClient + temp SQLite (aiosqlite).
- Fixtures in `conftest.py`: `DATABASE_URL=sqlite+aiosqlite:///...`, `APP_ENV=test`, `AUTO_CREATE_SCHEMA=true`.
- Tests clear `@lru_cache` on `get_settings()` between runs.

## Eval harness (`apps/api/src/.../evaluation/`)

- `python -m crewai_enterprise_pipeline_api.evaluation.runner --suite <name>`
- 5 suites, 11 scenarios. Isolated TestClient + temp SQLite per run.
- Do NOT modify scenario expectations without verifying service logic actually changed.
