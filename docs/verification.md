# Verification Gates

## Phase Completion Rule

No phase is considered complete until all of the following exist together:

1. Working code
2. Automated tests
3. Updated documentation
4. A reproducible demo path
5. Verification scripts
6. A stable baseline for the next phase

## Current Checks

The current gate now covers both the foundation and the first operations layer:

- backend app boot and schema lifecycle
- typed configuration loading
- persisted case workflow endpoints
- upload parsing, storage fallback, and evidence extraction
- issue-register creation and repeat-safe evidence scans
- checklist seeding, checklist updates, and completion coverage summaries
- approval review decisions and executive memo generation
- workflow run execution with trace events and generated report bundles
- persisted workstream synthesis outputs per run
- deterministic end-to-end evaluation scenarios with saved JSON scorecards
- repeat-scan regression checks for issue fingerprint reuse
- enforced-auth and role-guard tests
- request ID propagation on API responses
- readiness endpoint coverage
- source-adapter catalog exposure
- workbench dashboard rendering
- case workspace and run viewer rendering
- Docker stack validity
- lint, type, and unit test execution

## Initial Acceptance Criteria

- The API boots from the Conda environment without local path hacks.
- The API exposes environment-aware system endpoints.
- The API persists case, document, evidence, issue, request, and Q&A records.
- The API can ingest uploaded text documents into stored artifacts and evidence chunks.
- The issue register can be created manually and populated from evidence scans without duplicates.
- Checklist templates can be seeded, updated, and summarized into a completion-readiness view.
- Approval review can block export when mandatory coverage or high-severity issues remain open.
- Executive memo generation reflects live case state, open requests, top issues, and latest review status.
- A case can be executed into a persisted run with trace events and bundled markdown outputs.
- A run produces durable workstream syntheses for the first diligence domains.
- The first-slice evaluation suite passes blocked, clean-approved, and
  approved-nonblocking-risk scenarios.
- Every quality-gate run writes a machine-readable artifact under
  `artifacts/evaluations/`.
- Secured routes reject missing or under-privileged callers when auth is enforced.
- The API returns a request ID header on responses.
- The repo includes deployment, runbook, smoke-check, and release-checklist assets.
- The web app exposes a dashboard, case workspace, and run viewer over the shared case model.
- The workbench reflects the actual platform surface instead of generator boilerplate.
- The repo contains reproducible scripts for bootstrap, dev, and checks.
- Docker Compose starts the local backing services cleanly.
