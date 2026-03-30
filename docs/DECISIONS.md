# Architecture Decisions Log

> Key decisions, trade-offs, and rationale made during development.
> Any AI agent continuing work should read this to understand WHY, not just WHAT.

---

## AD-001: Deterministic fallback when no LLM key is present (2026-03-29)

**Decision:** When `LLM_API_KEY` is not set, the system must fall back to the existing deterministic
synthesis/report logic with a warning log. CrewAI agents are only activated when an LLM key is configured.

**Why:** The existing 24 pytest tests and 11 evaluation scenarios all assume deterministic output.
Breaking this would destroy the test safety net. Additionally, local development and CI should work
without requiring paid LLM API access.

**Impact:** workflow_service.py, synthesis_service.py, and report_service.py must always have a
working deterministic code path, even after CrewAI is wired in (Phase 7).

---

## AD-002: Keep header-based auth alongside JWT (2026-03-29)

**Decision:** When JWT auth is added in Phase 15, header-based auth (`X-CEP-User-*`) must continue
to work in `development` and `test` APP_ENV modes.

**Why:** All existing tests and evaluation scenarios use header-based auth. The smoke script and
manual testing also depend on it. Removing it would require rewriting the entire test infrastructure.

**Impact:** security.py must check APP_ENV first. In dev/test: use headers. In production: require JWT.
Both paths return the same `AuthenticatedPrincipal` object.

---

## AD-003: Pack model is combinatorial, not exclusive (2026-03-29)

**Decision:** Any motion_pack can combine with any sector_pack. The system must not hardcode
specific combinations. India rule packs are always active (determined by sector + evidence).

**Why:** The Codex original vision specified this. Business reality: a credit lender may be a
manufacturing company or a tech SaaS company. A vendor onboarding may target an NBFC.

**Impact:** Checklists, issue heuristics, agent prompts, and report templates must be composable.
checklist_service.py seeds by `motion_pack + sector_pack` combination. issue_service.py applies
rules from both packs. Report templates are motion_pack-specific.

---

## AD-004: SQLite for tests, PostgreSQL for production (2026-03-29)

**Decision:** Tests use `aiosqlite` with temp databases. Production uses `asyncpg` with PostgreSQL.

**Why:** Fast, isolated test runs without Docker. Each test gets a fresh database.

**Impact:** Some PostgreSQL-specific features (pgvector, GIN indexes, pg_trgm) cannot be tested
in unit tests. These will need integration tests against real Postgres (Phase 17). Use
`if dialect == 'postgresql'` guards where needed.

---

## AD-005: CaseRecord is the aggregate root (2026-03-29)

**Decision:** CaseRecord has cascade deletes to all child tables. Deleting a case removes everything.

**Why:** Simplifies data lifecycle management. A case is the unit of work in due diligence.

**Impact:** No orphan cleanup needed. All queries scope through case_id. Multi-tenancy (Phase 15)
adds org_id to CaseRecord, and the cascade propagates isolation naturally.

---

## AD-006: Evaluation harness is the primary quality gate, not pytest (2026-03-29)

**Decision:** The evaluation harness (11 scenarios across 5 suites) exercises the full HTTP flow
end-to-end. It is the release gate. pytest provides unit-level coverage but is secondary.

**Why:** Codex built this and it's the best thing in the codebase. It catches integration bugs
that unit tests miss. Each scenario creates a case, seeds a checklist, uploads documents, scans
issues, reviews, runs, and exports — then asserts on the full output.

**Impact:** Never modify evaluation scenario expectations without verifying the corresponding
service logic actually changed. New phases must add evaluation scenarios, not just pytest tests.

---

## AD-007: No Tailwind — pure CSS modules (2026-03-29)

**Decision:** The web frontend uses CSS modules with CSS custom properties. No Tailwind.

**Why:** Codex made this choice and it's deeply embedded. All existing styles use CSS modules.
Switching would require rewriting every component.

**Impact:** New components must use `*.module.css` files. Define shared variables in `globals.css`.

---

## AD-008: Word-boundary regex for issue heuristics (2026-03-30)

**Decision:** Replace naive substring matching (`pattern in text.lower()`) with word-boundary
regex (`re.search(r'\b' + re.escape(pattern) + r'\b', text, re.IGNORECASE)`).

**Why:** The old approach produced false positives -- "surcharge" would trigger the "charge"
pattern (encumbrance rule), "disclaimer" would trigger "claim" (litigation rule). Word-boundary
matching eliminates these while preserving all intended matches.

**Impact:** All 11 evaluation scenarios still pass at 100%, confirming no false negatives were
introduced. Issue heuristics are now stricter and more precise.

---

## AD-009: Reviewer decision override is optional (2026-03-30)

**Decision:** The `decision` field on `ApprovalDecisionCreate` is optional (defaults to None).
When None, the auto-computed logic applies. When provided, the reviewer's explicit decision
takes precedence.

**Why:** The previous system had no way for a reviewer to reject a case or conditionally approve
it -- the decision was purely computed from checklist coverage and blocking issues. Reviewers
need the ability to exercise judgment.

**Impact:** Existing tests and evaluation scenarios are unaffected (they don't send a decision
field). New enum values REJECTED and CONDITIONALLY_APPROVED are available for use.

---

## AD-010: Pagination on list_cases only (2026-03-30)

**Decision:** Add skip/limit pagination to GET /cases. Other list endpoints (documents, evidence,
issues, etc.) are not paginated yet because they are always scoped by case_id.

**Why:** Cases are the only unbounded list. Sub-resource lists are bounded by the case they
belong to and are typically small enough to return in full.

**Impact:** Frontend can paginate the case dashboard. Sub-resource pagination can be added later
if needed.

---

## AD-011: DELETE /cases cascade-deletes all children (2026-03-30)

**Decision:** DELETE /cases/{id} uses the existing CaseRecord cascade to remove all child records.

**Why:** CaseRecord is the aggregate root (AD-005). The cascade is already configured in the ORM.
A hard delete is simpler and safer than soft-delete for the current use case.

**Impact:** No orphan cleanup needed. All sub-resources are removed atomically.

---

## AD-012: Download endpoint uses full Response, not streaming (2026-03-30)

**Decision:** The export package download endpoint reads the full ZIP into memory and returns
it via `Response(content=...)` rather than `StreamingResponse`.

**Why:** Export ZIPs are currently small (< 1 MB). Streaming adds complexity without benefit at
this scale. Can be upgraded to StreamingResponse when large exports justify it.

**Impact:** Simple implementation. May need revisiting if export packages grow significantly.

---

## AD-013: background_mode defaults to false for sync fallback (2026-03-30)

**Decision:** The `background_mode` setting defaults to `false`. When false (or when Redis is
unreachable), POST /runs executes synchronously and returns `WorkflowRunResult`. When true and
Redis is available, it enqueues via arq and returns `WorkflowRunEnqueueResult`.

**Why:** All existing tests (50 pytest + 11 eval scenarios) assume synchronous execution and
inspect the completed run result immediately. Breaking this would destroy the test safety net.
Production deployments set `BACKGROUND_MODE=true` with Redis available.

**Impact:** The POST /runs endpoint returns a union type. Frontend must handle both response shapes.
Tests never need Redis or mocking (except the explicit enqueue test).

---

## AD-014: Redis dependency relaxed to >=5.0,<6 for arq compatibility (2026-03-30)

**Decision:** Changed redis pin from `==7.4.0` to `>=5.0,<6` because arq 0.27 requires `redis<6`.

**Why:** arq is the only production-grade async task queue for Python that integrates cleanly with
our existing asyncio/SQLAlchemy stack. The redis 5.x line is stable and the API differences from
7.x are negligible for our usage (basic get/set/pubsub).

**Impact:** Docker Compose still runs Redis 7.4 server. The Python `redis` client library is 5.x.
This is fine — the wire protocol is backward-compatible.

---

## AD-015: SSE stream polls at 1-second intervals (2026-03-30)

**Decision:** The SSE endpoint (`GET /runs/{id}/stream`) polls the database every second, emits
new trace events and status changes, and closes when the run reaches a terminal state.

**Why:** Simple implementation that works with SQLite tests and PostgreSQL production. A Redis
pub/sub approach would be more efficient but adds complexity for Phase 3. Can be upgraded later.

**Impact:** The endpoint is usable for the frontend run viewer in Phase 4. For long-running AI
runs (Phase 7+), the 1-second poll is adequate since runs take minutes, not milliseconds.

---

<!--
Template for future decisions:

## AD-XXX: Title (YYYY-MM-DD)

**Decision:** What was decided.

**Why:** Rationale, constraints, trade-offs.

**Impact:** What this means for future development.

---
-->
