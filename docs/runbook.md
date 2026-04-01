# Operations Runbook

## Core Endpoints

- `GET /api/v1/system/health`
- `GET /api/v1/system/readiness`
- `GET /api/v1/system/overview`
- `GET /api/v1/health/liveness`
- `GET /api/v1/health/readiness`
- `GET /api/v1/metrics`
- `GET /api/v1/admin/system/dependencies`
- `GET /api/v1/admin/system/llm/default`
- `POST /api/v1/cases/{case_id}/runs/{run_id}/export-package`

## Standard Checks

1. `./scripts/check.ps1`
2. Inspect the latest file under `artifacts/evaluations/`
3. `./scripts/evaluate.ps1 -Suite all`
4. `./scripts/smoke.ps1`
5. `./scripts/backup-db.ps1 -DryRun`
6. `docker compose -f docker-compose.prod.yml config`

## Production-Oriented Checks

- JWT smoke path:
  - `./scripts/smoke.ps1 -UseJwt`
- API reference refresh:
  - `./scripts/generate-api-reference.ps1`
- Full prod stack validation when Docker is available:
  - `./scripts/validate-prod-stack.ps1 -RequireLive`

## Runtime Status Surface

Use the workbench `/status` screen to inspect:

- dependency status and mode
- last check and last success timestamps
- failure reason
- org-default LLM provider/model

## Backup / Restore

- Backup dry-run:
  - `./scripts/backup-db.ps1 -DryRun`
- Backup:
  - `./scripts/backup-db.ps1`
- Restore dry-run:
  - `./scripts/restore-db.ps1 -BackupFile <path> -DryRun`
- Restore:
  - `./scripts/restore-db.ps1 -BackupFile <path>`

## Common Responses

### `401 Unauthorized`

- auth is enforced and neither a valid JWT nor the allowed dev/test headers were supplied

### `403 Forbidden`

- the caller authenticated but does not have the required role or org scope

### `429 Rate limit exceeded`

- the caller exceeded the configured bucket for auth, connector, mutating, or read traffic

### `readiness = degraded` or `failed`

- one or more dependencies are unavailable, stubbed, or unconfigured for the active environment

## Artifact Locations

- evaluation scorecards: `artifacts/evaluations/`
- regression baseline: `artifacts/baselines/`
- generated API reference: `docs/api-reference.md`
- database backups: `artifacts/backups/`
- local uploaded files in dev/test: `storage/`
