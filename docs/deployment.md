# Deployment Guide

## Scope

Phase 18 adds the production-shaped packaging layer:

- multi-stage Dockerfiles for `apps/api` and `apps/web`
- baked-config Dockerfiles for Prometheus, Grafana, and Tempo
- `docker-compose.prod.yml` with named volumes only
- a dedicated `migrate` service for Alembic upgrades
- backup / restore scripts
- generated API-reference docs

This means the repo now has a serious release packaging story, but the final
release label still depends on live validation of the production stack and the
strict live LLM / connector suites in an environment that actually has Docker
and real credentials.

## Production Services

- `postgres`
- `redis`
- `minio`
- `tempo`
- `prometheus`
- `grafana`
- `migrate`
- `api`
- `worker`
- `web`

## Environment Contract

Start from `.env.example` and set at least:

### Core runtime

- `APP_ENV=production`
- `DATABASE_URL` or `POSTGRES_*`
- `REDIS_HOST`, `REDIS_PORT`
- `MINIO_ENDPOINT`, `MINIO_ROOT_USER`, `MINIO_ROOT_PASSWORD`, `MINIO_BUCKET_NAME`
- `STORAGE_BACKEND`
- `LOCAL_STORAGE_ROOT`

### Auth and tenancy

- `ENFORCE_AUTH=true`
- `JWT_SECRET`
- `JWT_ALGORITHM`
- `JWT_ACCESS_TOKEN_EXPIRES_SECONDS`
- `DEFAULT_ORG_ID`, `DEFAULT_ORG_NAME`, `DEFAULT_ORG_SLUG`
- `DEFAULT_API_CLIENT_ID`, `DEFAULT_API_CLIENT_SECRET`

### LLM / connectors

- `LLM_PROVIDER`
- `LLM_API_KEY`
- `LLM_MODEL`
- `LLM_BASE_URL`
- connector keys/base URLs such as `MCA21_API_KEY`, `GSTIN_API_KEY`, `ROC_API_KEY`

### Observability and ports

- `OTEL_EXPORTER_OTLP_ENDPOINT`
- `API_PORT`, `WEB_PORT`
- `PROMETHEUS_PORT`, `GRAFANA_PORT`, `TEMPO_UI_PORT`, `OTLP_GRPC_PORT`

### Backups

- `BACKUP_RETENTION_DAYS`
- `BACKUP_S3_UPLOAD_ENABLED`
- `BACKUP_S3_ENDPOINT`
- `BACKUP_S3_BUCKET`
- `BACKUP_S3_ACCESS_KEY`
- `BACKUP_S3_SECRET_KEY`

## Local Development Bring-Up

1. `./scripts/bootstrap.ps1`
2. `./scripts/dev-stack.ps1`
3. `./scripts/dev-api.ps1`
4. `./scripts/dev-web.ps1`
5. `./scripts/check.ps1`
6. `./scripts/smoke.ps1`

## Production Packaging Flow

1. Copy `.env.example` to `.env` and replace all default secrets.
2. Generate the API reference:
   - `./scripts/generate-api-reference.ps1`
3. Validate the production compose file:
   - `docker compose -f docker-compose.prod.yml config`
4. Dry-run the backup plan:
   - `./scripts/backup-db.ps1 -DryRun`
5. Build and boot the production stack when Docker is available:
   - `./scripts/validate-prod-stack.ps1 -RequireLive`

`validate-prod-stack.ps1` will:

- build the production images
- start the compose stack
- run the JWT-based smoke test
- tear the stack down afterward

## Backup and Restore

### Backup

- Dry-run:
  - `./scripts/backup-db.ps1 -DryRun`
- Real backup:
  - `./scripts/backup-db.ps1`

The script prefers local `pg_dump` and falls back to Docker execution when
needed. Old backups are pruned by retention days. Optional S3/MinIO upload is
controlled through the `BACKUP_S3_*` environment variables.

### Restore

- Dry-run:
  - `./scripts/restore-db.ps1 -BackupFile .\\artifacts\\backups\\<file>.sql -DryRun`
- Real restore:
  - `./scripts/restore-db.ps1 -BackupFile .\\artifacts\\backups\\<file>.sql`

The restore script prefers local `psql` and falls back to Docker execution when
needed.

## Upgrade / Rollback / Recovery

### Upgrade

1. Refresh `.env`
2. `docker compose -f docker-compose.prod.yml config`
3. `./scripts/generate-api-reference.ps1`
4. `./scripts/backup-db.ps1`
5. `./scripts/validate-prod-stack.ps1 -RequireLive`

### Rollback

1. Stop the new stack
2. Restore the previous image tags / branch state
3. Restore the last good backup with `restore-db.ps1`
4. Re-run `validate-prod-stack.ps1 -RequireLive`

### Disaster recovery

1. Recreate infrastructure from `docker-compose.prod.yml`
2. Restore the most recent retained backup
3. Re-run smoke checks
4. Confirm readiness and `/status` dependency health

## Current Validation Caveat

`docker compose -f docker-compose.prod.yml config` is already verified in this
repo. Live production boot validation is implemented but was not completed in
this environment because Docker Desktop was unavailable from the current shell.
