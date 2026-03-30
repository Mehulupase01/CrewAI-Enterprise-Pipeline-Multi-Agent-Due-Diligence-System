---
description: Testing approach and quality gates for this project
globs: ["apps/api/tests/**/*.py", "apps/api/src/**/evaluation/**/*.py"]
---

## Two-layer testing

This project uses two complementary test layers:

### 1. pytest unit tests (`apps/api/tests/`)

- Run with: `python -m pytest` from `apps/api/`
- Use `FastAPI TestClient` with temp SQLite databases (not Postgres).
- Fixtures in `conftest.py` set `DATABASE_URL=sqlite+aiosqlite:///...`, `APP_ENV=test`, `AUTO_CREATE_SCHEMA=true`, local storage.
- Tests clear the `@lru_cache` on `get_settings()` between runs.
- Test files: `test_cases.py`, `test_health.py`, `test_security.py`, `test_source_adapters.py`, `test_evaluation.py`.

### 2. Evaluation scenarios (`apps/api/src/.../evaluation/`)

- Run with: `python -m crewai_enterprise_pipeline_api.evaluation.runner --suite <name>`
- Scenario-based integration harness exercising full HTTP flows (case create -> upload -> scan -> approve -> run -> export).
- Each scenario defines `EvaluationScenario` with payloads and `ScenarioExpectation` assertions.
- Creates isolated TestClient with temp SQLite per run.
- Outputs JSON scorecards to `artifacts/evaluations/`.
- 5 suites, 11 scenarios total. All must pass for a complete verification.
- This is the primary integration test surface and the quality gate for releases.

## When to run what

- After changing service logic, domain models, or routes: run both `pytest` and the relevant evaluation suite.
- After changing checklist templates or issue heuristics: run the evaluation suite that covers that motion/sector pack.
- After changing web types or fetch layer: run `npm run lint && npm run typecheck`.
- Before any commit: run `./scripts/check.ps1` (runs everything).

## Test data

- pytest uses inline fixtures and temp databases.
- Evaluation scenarios define their own case payloads, documents, and expectations in `scenarios.py`.
- The web app has hardcoded demo data in `workbench-data.ts` for offline UI development.
- Do not modify evaluation scenario expectations without verifying the corresponding service logic actually changed.
