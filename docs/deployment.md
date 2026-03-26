# Deployment Guide

## Purpose

This project is still local-first, but the first flagship slice now has a
clear deployment shape for internal environments.

## Services

- FastAPI API service
- Next.js workbench
- PostgreSQL
- Redis
- MinIO-compatible object storage

## Required Environment Variables

### API

- `APP_ENV`
- `DATABASE_URL` or the `POSTGRES_*` variables
- `REDIS_HOST`
- `REDIS_PORT`
- `MINIO_ENDPOINT`
- `MINIO_ROOT_USER`
- `MINIO_ROOT_PASSWORD`
- `STORAGE_BACKEND`
- `LOCAL_STORAGE_ROOT`
- `ENFORCE_AUTH`
- `DEFAULT_ACTOR_ROLE`

### Web

- the web app currently expects the API at the local default unless overridden

## Local Bring-Up

1. Run `./scripts/bootstrap.ps1`
2. Run `./scripts/dev-stack.ps1`
3. Run `./scripts/dev-api.ps1`
4. Run `./scripts/dev-web.ps1`
5. Run `./scripts/check.ps1`
6. Optionally run `./scripts/smoke.ps1`

## Auth Modes

- Development and test default to bypass mode unless `ENFORCE_AUTH=true`
- Production-shaped environments should set `APP_ENV=production` or
  `ENFORCE_AUTH=true`
- When auth is enforced, secured endpoints expect:
  - `X-CEP-User-Id`
  - `X-CEP-User-Name`
  - `X-CEP-User-Email`
  - `X-CEP-User-Role`

## Production-Shaped Notes

- terminate TLS upstream of the API and web app
- use managed Postgres and object storage where possible
- keep evaluation artifacts in durable storage if CI generates them
- rotate default credentials before any shared-environment deployment
- run the smoke script and readiness endpoint checks after rollout
