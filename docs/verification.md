# Verification Gates

## Phase Completion Rule

No phase is considered complete until all of the following exist together:

1. Working code
2. Automated tests
3. Updated documentation
4. A reproducible demo path
5. Verification scripts
6. A stable baseline for the next phase

## Foundation Checks

The current foundation gate focuses on:

- backend app boot
- typed configuration loading
- basic system endpoints
- web workbench shell rendering
- Docker stack validity
- lint and unit test execution

## Initial Acceptance Criteria

- The API boots from the Conda environment without local path hacks.
- The API exposes environment-aware system endpoints.
- The workbench reflects the planned product shape instead of generator boilerplate.
- The repo contains reproducible scripts for bootstrap, dev, and checks.
- Docker Compose starts the local backing services cleanly.
