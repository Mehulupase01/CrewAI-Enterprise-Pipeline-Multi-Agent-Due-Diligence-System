# Release Checklist

## Before Release

- `./scripts/check.ps1` passes
- `./scripts/smoke.ps1` passes against the running API
- latest evaluation artifact exists under `artifacts/evaluations/`
- `GET /api/v1/system/readiness` returns `ready`
- auth mode is confirmed for the target environment
- default credentials are removed from shared environments
- README and docs match the repo state

## First-Slice Functional Checks

- create and inspect a case
- seed checklist items
- upload a document and verify evidence creation
- run issue scan and confirm no duplicate issue creation on rerun
- execute reviewer approval
- execute a workflow run and inspect report bundles
- open the case and run views in the web workbench
