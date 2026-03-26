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
- source-adapter catalog exposure
- workbench dashboard rendering
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
- The workbench reflects the actual platform surface instead of generator boilerplate.
- The repo contains reproducible scripts for bootstrap, dev, and checks.
- Docker Compose starts the local backing services cleanly.
