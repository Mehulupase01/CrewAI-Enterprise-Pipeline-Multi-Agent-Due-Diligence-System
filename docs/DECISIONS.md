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

<!--
Template for future decisions:

## AD-XXX: Title (YYYY-MM-DD)

**Decision:** What was decided.

**Why:** Rationale, constraints, trade-offs.

**Impact:** What this means for future development.

---
-->
