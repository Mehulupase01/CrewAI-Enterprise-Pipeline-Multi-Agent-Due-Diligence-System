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

## AD-016: Semantic chunking uses heading-first splitting (2026-03-30)

**Decision:** The chunker splits text by section headings first, then by paragraphs within
each section, then by sentence boundaries for oversized paragraphs. Chunk max is 1200 chars.

**Why:** Heading-aware chunks preserve document structure, making them more useful for evidence
extraction and future embedding-based search. Sentence splitting is the last resort to keep
chunks under the size limit.

**Impact:** ChunkRecord carries section_title, page_number, char_start, char_end. Phase 5
embeddings will benefit from semantically coherent chunks.

---

## AD-017: Entity extraction is rule-based, not LLM-dependent (2026-03-30)

**Decision:** The entity extractor uses regex patterns to identify financial metrics, legal
entities, regulatory identifiers, and India-specific numbers (CIN, GSTIN).

**Why:** Deterministic extraction is testable, fast, and doesn't require API keys. India-specific
formats (CIN: 21 chars, GSTIN: 15 chars) have rigid structures ideal for regex. LLM-based
extraction can be layered on top in Phase 7 when CrewAI agents are wired.

**Impact:** All evaluation scenarios continue to pass. Entity evidence has higher confidence
(0.8-0.95) than chunk-based evidence (0.75).

---

## AD-018: Document dedup by SHA256 digest (2026-03-30)

**Decision:** Before creating a new DocumentArtifactRecord, check if the same SHA256 digest
already exists for the case. If so, return the existing artifact with zero new evidence.

**Why:** Users may accidentally upload the same file twice. Without dedup, this creates
duplicate evidence and chunks, inflating issue counts and confusing analysis.

**Impact:** Second upload of identical content is a no-op that returns the existing artifact.
Different files with the same name but different content are NOT deduped (content-based, not
name-based).

---

## AD-019: Embeddings stored as raw float32 bytes in LargeBinary (2026-03-30)

**Decision:** Store embedding vectors as raw little-endian float32 bytes in a `LargeBinary` column rather than using pgvector's native `Vector` type in the ORM.

**Why:** SQLite (used for all tests) has no pgvector support. By storing raw bytes, the ORM works identically on both SQLite and PostgreSQL. The Alembic migration adds the actual `vector(1536)` column and HNSW/GIN indexes for PostgreSQL only. Cosine similarity is computed in pure Python for SQLite and via pgvector operators for PostgreSQL.

**Impact:** Tests work without PostgreSQL. Production gets full pgvector performance via the migration.

---

## AD-020: Embedding provider defaults to "none" (2026-03-30)

**Decision:** The `embedding_provider` setting defaults to `"none"`. When set to `"none"`, embedding generation is skipped and search falls back to keyword-only matching.

**Why:** Consistent with AD-001 (deterministic fallback). Tests and local development work without OpenAI API keys. Production sets `EMBEDDING_PROVIDER=openai` with a key.

**Impact:** Search always works (keyword fallback). Embedding-enhanced search activates only with explicit configuration.

---

## AD-021: Conflict detection with embedding + text fallback (2026-03-30)

**Decision:** Evidence conflict detection uses cosine similarity between embeddings when available. Falls back to Jaccard word overlap when embeddings are absent. Thresholds: >0.98 = DUPLICATE, >0.92 with different values = CONTRADICTORY.

**Why:** Embedding-based comparison is more accurate but requires the embedding provider to be active. The text overlap fallback ensures the feature works in all environments, including tests.

**Impact:** The `/evidence/conflicts` endpoint always returns results. Accuracy improves when embeddings are enabled.

---

## AD-022: Direct fetch() through Next.js proxy, not Server Actions (2026-03-31)

**Decision:** Client components use direct `fetch()` calls to the FastAPI backend through a Next.js `rewrites` proxy (`/api/v1/*` → `http://127.0.0.1:8000/api/v1/*`), rather than Next.js Server Actions.

**Why:** All mutations target an external FastAPI backend, not Next.js internal routes. Server Actions would add an unnecessary indirection layer (client → Next.js server → FastAPI) with no benefit. The proxy approach avoids CORS while keeping the mutation path simple: client → proxy → FastAPI.

**Impact:** All interactive components use `fetch()` directly. The proxy is configured in `next.config.ts`. No Server Actions exist in the codebase.

---

## AD-023: router.refresh() for server component revalidation (2026-03-31)

**Decision:** After every mutation (create, update, delete), client components call `router.refresh()` from `next/navigation` to revalidate the parent server component's data.

**Why:** The case workspace page is a server component that fetches data on the server. Client components perform mutations but cannot directly update the server component's state. `router.refresh()` triggers a soft re-render of the page without a full navigation, re-fetching server data.

**Impact:** Simple and reliable pattern. No client-side caching or state management needed. Small overhead per mutation (one extra server fetch) but acceptable for this use case.

---

## AD-024: Sequential crew process for workstream analysis (2026-03-31)

**Decision:** CrewAI uses `Process.sequential` — each workstream agent runs independently in sequence, then the coordinator synthesizes all outputs. No hierarchical delegation between agents.

**Why:** Workstream analyses are independent — the financial analyst doesn't need the legal analyst's output. Sequential execution is simpler, more predictable, and easier to debug. Hierarchical process would add a manager agent that delegates, adding latency and token cost without improving quality for this use case.

**Impact:** Each agent task runs one after another. The coordinator task has `context=tasks` to receive all prior outputs. If parallelism is needed later, CrewAI supports `async_execution=True` on individual tasks.

---

## AD-025: Pre-loaded context, no custom agent tools (2026-03-31)

**Decision:** All case data (evidence, issues, checklist items) is queried once before crew kickoff and passed in the task description. Agents do not have custom tools to query the database.

**Why:** CrewAI tools run synchronously, but all our services are async. Bridging async→sync in a threaded context is fragile. Pre-loading avoids this entirely, makes tests work without LLM calls, and ensures agents analyze the exact same snapshot of data. Custom tools can be added in a later phase when agents need to search or drill down.

**Impact:** Agent prompts include formatted evidence, issues, and checklist items directly. Task descriptions can be long but are within LLM context limits. Database queries happen before the crew starts.

---

## AD-026: Crew runs in asyncio.to_thread, trace events written post-completion (2026-03-31)

**Decision:** `crew.kickoff()` runs in a thread via `asyncio.to_thread()` to avoid blocking the async event loop. Trace events are written to the database after the crew completes, not during execution.

**Why:** CrewAI's `kickoff()` is synchronous and can run for minutes. Blocking the FastAPI event loop would stall all other requests. Writing trace events mid-execution would require thread-safe async database access, adding significant complexity. Post-completion writing is simple and the SSE endpoint still picks up events on its 1-second poll.

**Impact:** The SSE live viewer will show crew_initialized → (pause while crew runs) → all agent events at once → report_bundle_generation. Real-time per-step streaming can be added later via CrewAI's `step_callback` + a thread-safe queue.

---

## AD-027: LLM settings default to none — consistent with AD-001 pattern (2026-03-31)

**Decision:** `llm_provider` defaults to `"none"` and `llm_api_key` defaults to `None`. CrewAI agents only activate when both are explicitly set.

**Why:** Consistent with AD-001 (deterministic fallback) and AD-020 (embedding provider defaults). All existing tests and evaluation scenarios work without API keys. Production deployments set `LLM_PROVIDER=openai` and `LLM_API_KEY=sk-...` in the environment.

**Impact:** Zero behavior change for existing users. CrewAI is opt-in via environment variables. The `_crew_available()` guard in WorkflowService checks both settings.

---

## AD-028: Roadmap documents guide direction, but repo state is execution truth (2026-03-31)

**Decision:** `docs/MASTERPLAN.docx` is the preferred machine-readable roadmap source, with `docs/MASTERPLAN.pdf` as its presentation/export companion. Both define intended direction, but implementation decisions during execution must be grounded in actual code, tests, runnable commands, and verified outputs.

**Why:** Long-running flagship projects often accumulate drift between strategy documents and repo reality. Without an explicit rule, future sessions can optimize against stale planning text and misreport progress.

**Impact:** Every resumed session should read the roadmap, then verify the live repo before deciding the next phase. If docs are stale, they must be repaired after the relevant phase is completed.

---

## AD-029: One phase must be fully closed before the next phase is claimed (2026-03-31)

**Decision:** For this repo, phases are completed one at a time. A phase is only closed when code, tests, docs, and continuity artifacts (`CLAUDE.md`, `HANDOFF.md`, `PROGRESS.md`, `DECISIONS.md`, `architecture.md`) agree.

**Why:** This project is large enough that "mostly done" creates false confidence and destroys session continuity. Explicit phase closure keeps the roadmap, repo state, and handoff artifacts aligned.

**Impact:** Future sessions should avoid batching multiple phases together unless the user explicitly asks for it. Work that does not fully close the current phase should be reported as in progress, not complete.

---

## AD-030: CrewAI tools operate on pre-loaded case snapshots, not live async queries (2026-03-31)

**Decision:** A post-Phase-7 enhancement replaces prompt-only deep context with scoped read-only CrewAI tools for evidence search, issue review, and checklist-gap review. These tools operate on a case snapshot built before kickoff, including eagerly loaded document chunks.

**Why:** This keeps the CrewAI path context-efficient without reintroducing the async-to-sync bridging risk called out in AD-025. Agents can drill down into the evidence they need without stuffing the full case state into every task description.

**Impact:** `build_case_context()` must preload chunk metadata, `case_service._get_case_record()` must eagerly load document chunks, and the deterministic fallback remains untouched. Tool builders are pure in-memory adapters over the preloaded snapshot.

---

## AD-031: Tool usage is summarized in persisted run traces after crew completion (2026-03-31)

**Decision:** Tool instances record lightweight usage logs locally during the CrewAI run. After kickoff completes, workflow trace events include per-workstream and coordinator tool usage summaries plus a total tool-call count in the report-generation step.

**Why:** This adds auditability for the LLM path without introducing thread-safe live database writes or a mid-run event queue. It improves reviewability while keeping the execution model aligned with AD-026.

**Impact:** The SSE viewer still observes events after completion rather than true live tool streaming. A future phase can add step-level callbacks and a queue-backed streaming bridge if the roadmap requires real-time agent telemetry.

---

## AD-032: Phase 8 financial summaries are computed on demand, not stored as a separate table (2026-03-31)

**Decision:** The QoE engine computes the case financial summary from uploaded financial artifacts on demand and refreshes it inside workflow execution before coverage, approvals, syntheses, and reports. It is not persisted as a separate derived database table in Phase 8.

**Why:** The financial summary is fully derivable from stored artifacts plus deterministic parsing logic. Persisting it would add schema churn, stale-data risk, and migration overhead for a phase that is still refining extraction logic.

**Impact:** `financial_qoe_service.py` is the single source of truth for Phase 8 ratios, normalized EBITDA, and flags. Workflow execution must call the QoE refresh before downstream report and approval logic.

---

## AD-033: Financial metric matching prefers exact and longer aliases over generic substrings (2026-03-31)

**Decision:** Financial label normalization ranks exact alias matches ahead of word-boundary matches and prefers longer aliases over shorter generic ones.

**Why:** A naive substring strategy caused real extraction errors: `EBITDA` could be consumed by the generic `EBIT` alias, and `Q4 Revenue Share` could be misread as `revenue`. Phase 8 needs deterministic and trustworthy parsing for downstream ratios and checklist automation.

**Impact:** New aliases in `financial_parser.py` must remain specific and test-backed. Parser regressions in label resolution should be treated as high-severity because they silently distort downstream QoE metrics.

---

## AD-034: Financial checklist automation happens by default when the summary endpoint is called (2026-03-31)

**Decision:** `GET /cases/{id}/financial-summary` persists checklist auto-satisfaction by default, with `persist_checklist=false` available for dry-run access.

**Why:** The master plan explicitly requires automatic checklist satisfaction for financial workstream items. Doing this only inside the workflow path would make direct analyst and evaluation access inconsistent with the canonical phase behavior.

**Impact:** The financial summary endpoint has stateful side effects by default. Callers that need read-only inspection must opt out explicitly.

---

## AD-035: CrewAI financial workstreams consume structured QoE state plus benchmarks, not only narrative prompt context (2026-03-31)

**Decision:** The financial workstream and coordinator receive a structured financial snapshot plus dedicated financial ratio and benchmark tools during CrewAI runs.

**Why:** Phase 8 is about deterministic financial depth, not just richer prose. If the CrewAI path continued to rely on generic narrative-only prompts, the QoE engine would not materially improve the LLM execution path.

**Impact:** `agents/financial_tools.py`, `agents/tools.py`, and `agents/crew.py` are now part of the canonical financial analysis surface. Future financial phases should extend these structured tools before adding more prompt text.

---

<!--
Template for future decisions:

## AD-XXX: Title (YYYY-MM-DD)

**Decision:** What was decided.

**Why:** Rationale, constraints, trade-offs.

**Impact:** What this means for future development.

---
-->
