---
description: Code style and naming conventions for this project
globs: ["apps/api/**/*.py", "apps/web/**/*.ts", "apps/web/**/*.tsx", "apps/web/**/*.css"]
---

## Python (apps/api/)

- Python 3.12 strict. Use modern syntax (UP rules enabled).
- Ruff linter with rules B, E, F, I, N, UP. Line length 100.
- Import sorting via ruff isort. First-party package: `crewai_enterprise_pipeline_api`.
- Classes: `PascalCase`. Functions/variables: `snake_case`. Enums: `StrEnum`.
- SQLAlchemy ORM classes end in `Record` (e.g., `CaseRecord`, `EvidenceNodeRecord`).
- Service classes end in `Service` (e.g., `CaseService`, `WorkflowService`).
- Pydantic schemas: `*Create` (input), `*Summary` (list response), `*Detail` (full response), `*Result` (action response).
- All domain enums and Pydantic schemas go in `domain/models.py`. ORM models go in `db/models.py`. Keep these strictly separate.
- All DB and storage I/O must be async/await. Use `AsyncSession` from `db/session.py`.
- Services compose other services via constructor injection, not inheritance.
- UUIDs from `uuid4()` in `db/base.py`. All timestamps UTC via `TimestampedMixin`.
- Service methods return `None` for not-found; routers convert to `HTTPException(404)`.
- File encoding: UTF-8, LF line endings, 4-space indentation (per .editorconfig).

## TypeScript (apps/web/)

- TypeScript strict mode. Next.js 16 App Router with server components.
- Path alias: `@/*` maps to `./src/*`.
- Type definitions in `src/lib/workbench-data.ts` must mirror API domain enums and response shapes.
- No Tailwind -- use CSS modules with CSS custom properties defined in `globals.css`.
- File encoding: UTF-8, LF line endings, 2-space indentation.
