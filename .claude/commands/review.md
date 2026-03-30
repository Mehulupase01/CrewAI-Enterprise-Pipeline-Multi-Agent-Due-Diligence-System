Review the code changes in the current branch or staged files for this project.

Steps:
1. Run `git diff --cached` to see staged changes. If empty, run `git diff` for unstaged changes. If both empty, run `git diff main...HEAD` for branch changes.
2. For each changed file, check:
   - **Python (apps/api/):** Ruff compliance (line-length 100, rules B/E/F/I/N/UP). Async/await correctness. Pydantic schema consistency with domain/models.py. ORM model changes in db/models.py must not break cascade relationships from CaseRecord. Service composition pattern (constructor, not inheritance). No breaking changes to template_key values in checklist_service.py or enum values in domain/models.py.
   - **TypeScript (apps/web/):** Strict mode compliance. Type definitions in workbench-data.ts must stay in sync with domain/models.py enums and schemas. CSS module class usage.
   - **Cross-cutting:** API contract changes (routes, request/response shapes) must be reflected in both API domain models and web workbench-data.ts types. Evaluation scenarios in scenarios.py must still pass if domain enums or checklist templates changed.
3. Run `cd apps/api && python -m ruff check src tests` to verify lint.
4. Run `cd apps/api && python -m pytest` to verify tests pass.
5. Summarize findings: what looks good, what needs attention, any contract mismatches between API and web.
