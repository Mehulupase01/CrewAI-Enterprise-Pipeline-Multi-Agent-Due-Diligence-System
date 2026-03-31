---
description: Code style details (loaded only when editing source files)
paths: ["apps/api/**/*.py", "apps/web/**/*.ts", "apps/web/**/*.tsx"]
---

## Python (apps/api/)

- Python 3.12, Ruff rules: B, E, F, I, N, UP. Line length 100.
- Import sorting: ruff isort, first-party: `crewai_enterprise_pipeline_api`.
- Enums: `StrEnum`. UUIDs: `uuid4()` in `db/base.py`. Timestamps: UTC via `TimestampedMixin`.
- Service methods return `None` for not-found; routers convert to `HTTPException(404)`.

## TypeScript (apps/web/)

- Strict mode. Next.js 16 App Router. Path alias: `@/*` → `./src/*`.
- Types in `src/lib/workbench-data.ts` mirror API domain enums.
- CSS modules only. 2-space indent.
