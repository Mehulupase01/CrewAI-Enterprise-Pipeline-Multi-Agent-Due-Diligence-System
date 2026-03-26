# Operations Runbook

## Core Endpoints

- `GET /api/v1/system/health`
- `GET /api/v1/system/readiness`
- `GET /api/v1/system/overview`
- `GET /api/v1/source-adapters`
- `POST /api/v1/cases/{case_id}/runs/{run_id}/export-package`

## Standard Checks

1. Run `./scripts/check.ps1`
2. Inspect the latest file under `artifacts/evaluations/`
3. Run `./scripts/evaluate.ps1 -Suite all` if you want a fresh multi-suite artifact across buy-side, credit, vendor, manufacturing, and BFSI
4. Run `./scripts/smoke.ps1` against the live API

## What Readiness Means Right Now

- database connection succeeds
- storage mode is configured
- at least one evaluation artifact can be discovered, if available

## Common Responses

### `401 Unauthorized`

- auth is enforced and the `X-CEP-*` headers are missing

### `403 Forbidden`

- the caller authenticated, but the role does not have route permission

### `readiness = degraded`

- database connectivity failed, or another core check could not complete

## Artifact Locations

- evaluation scorecards: `artifacts/evaluations/`
- local uploaded files in dev/test: `storage/`
