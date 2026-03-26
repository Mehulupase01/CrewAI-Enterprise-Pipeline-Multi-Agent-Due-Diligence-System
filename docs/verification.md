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
- source-adapter catalog exposure
- workbench dashboard rendering
- Docker stack validity
- lint, type, and unit test execution

## Initial Acceptance Criteria

- The API boots from the Conda environment without local path hacks.
- The API exposes environment-aware system endpoints.
- The API persists case, document, evidence, request, and Q&A records.
- The workbench reflects the actual platform surface instead of generator boilerplate.
- The repo contains reproducible scripts for bootstrap, dev, and checks.
- Docker Compose starts the local backing services cleanly.
