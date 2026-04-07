# External Actions Checklist

> Everything below requires **your action** -- credentials, infrastructure, or manual verification
> that cannot be completed by code alone. The codebase is 100% code-complete.

Last updated: 2026-04-08

---

## 1. LLM / AI Provider Setup

| # | Action | .env Variable(s) | How |
|---|--------|-------------------|-----|
| 1.1 | Get an OpenRouter API key (or OpenAI/Anthropic direct) | `LLM_PROVIDER`, `LLM_API_KEY`, `LLM_MODEL`, `LLM_BASE_URL` | Sign up at openrouter.ai, create API key. Set `LLM_PROVIDER=openai`, `LLM_BASE_URL=https://openrouter.ai/api/v1`, `LLM_MODEL=openai/gpt-4o-mini` (or any model) |
| 1.2 | Get an embedding provider key (optional) | `EMBEDDING_PROVIDER`, `EMBEDDING_API_KEY`, `EMBEDDING_MODEL` | Set `EMBEDDING_PROVIDER=openai`, provide key. Only needed for semantic search (pgvector hybrid). System works without it using full-text search fallback |
| 1.3 | Choose default org LLM model | Via admin API or workbench `/status` screen | After API is running: `PATCH /api/v1/admin/system/llm/default` or use the Status Control Center in the web UI |

**Verification:** Once configured, create a test case and run a workflow. Check that `execution_mode` in the run trace shows `"crew"` instead of `"deterministic"`.

---

## 2. India Data Connector Credentials

| # | Connector | .env Variable(s) | Notes |
|---|-----------|-------------------|-------|
| 2.1 | MCA21 (Company Master Data) | `MCA21_API_BASE_URL`, `MCA21_API_KEY` | Government API. May require registration with MCA portal or use a third-party aggregator (e.g., Tofler, Zaubacorp API) |
| 2.2 | GSTIN (GST Verification) | `GSTIN_API_BASE_URL`, `GSTIN_API_KEY` | Available through GST portal API or third-party providers (e.g., ClearTax, Masters India) |
| 2.3 | SEBI SCORES | `SEBI_SCORES_API_BASE_URL`, `SEBI_SCORES_API_KEY` | SEBI complaint/disclosure data. May need scraping adapter or third-party provider |
| 2.4 | RoC Filings | `ROC_API_BASE_URL`, `ROC_API_KEY` | RoC charges, orders. Similar to MCA21 sourcing |
| 2.5 | CIBIL Bureau | `CIBIL_API_BASE_URL`, `CIBIL_API_KEY` | Requires commercial agreement with TransUnion CIBIL. Currently operates as stub |
| 2.6 | Sanctions Lists | `SANCTIONS_OFAC_URL`, `SANCTIONS_MCA_URL`, `SANCTIONS_SEBI_URL` | OFAC SDN list is publicly available. MCA disqualified directors and SEBI debarred lists can be sourced from respective regulator websites |

**Verification:** Run `GET /api/v1/source-adapters` -- adapters should show `status: "available"` instead of `"stub"`. Then test with `POST /api/v1/cases/{id}/source-adapters/{adapter}/fetch`.

---

## 3. Docker & Production Stack

| # | Action | How |
|---|--------|-----|
| 3.1 | Install/start Docker Desktop | Install Docker Desktop for Windows. Ensure the daemon is running |
| 3.2 | Validate production stack | Run `./scripts/validate-prod-stack.ps1`. This spins up the full `docker-compose.prod.yml` (Postgres, Redis, MinIO, API, Worker, Web, Prometheus, Grafana, Tempo), runs smoke tests, and tears down |
| 3.3 | Run live OpenRouter validation | Set `PHASE17_ENABLE_LIVE_VALIDATION=true` in `.env`, then run `./scripts/validate-prod-stack.ps1 -RequireLive` |
| 3.4 | Run live connector validation | Set connector credentials + `PHASE17_ENABLE_LIVE_VALIDATION=true`, then run the validation script |

---

## 4. Production Secrets & Security

| # | Action | .env Variable(s) | Notes |
|---|--------|-------------------|-------|
| 4.1 | Generate a strong JWT secret | `JWT_SECRET` | Must be 32+ bytes random string. Example: `openssl rand -hex 32` |
| 4.2 | Set real database credentials | `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` | Do NOT use defaults (`crewai`/`crewai`) in production |
| 4.3 | Set real MinIO credentials | `MINIO_ROOT_USER`, `MINIO_ROOT_PASSWORD` | Do NOT use defaults (`minioadmin`/`minioadmin`) in production |
| 4.4 | Set real API client secret | `DEFAULT_API_CLIENT_SECRET` | Used for JWT token generation via `POST /api/v1/auth/token` |
| 4.5 | Enable auth enforcement | `ENFORCE_AUTH=true` | Required for non-dev environments. Enables JWT bearer auth on all endpoints |
| 4.6 | Set app environment | `APP_ENV=production` | Switches to JSON logging, strict auth, disables auto schema creation |

---

## 5. Production Deployment

| # | Action | How |
|---|--------|-----|
| 5.1 | Provision target server/cloud | AWS, GCP, Azure, or bare metal with Docker support |
| 5.2 | Create production `.env` | Copy `.env.example` to `.env`, fill all real values from sections 1-4 above |
| 5.3 | Deploy with docker-compose | `docker compose -f docker-compose.prod.yml up -d` |
| 5.4 | Run database migration | Handled automatically by the `migrate` service in docker-compose.prod.yml |
| 5.5 | Configure DNS / reverse proxy | Point your domain to the API (port 8000) and web (port 3000) services |
| 5.6 | Set up TLS/HTTPS | Use nginx/caddy/ALB as reverse proxy with SSL certificates |

---

## 6. Observability Endpoints

| # | Action | .env Variable(s) | Notes |
|---|--------|-------------------|-------|
| 6.1 | Configure OTLP exporter | `OTEL_EXPORTER_OTLP_ENDPOINT` | Point to your Tempo/Jaeger/Datadog trace collector |
| 6.2 | Access Grafana dashboards | Grafana runs at port 3001 in the prod stack | Default creds: `admin`/`admin`. Change via `GRAFANA_ADMIN_PASSWORD` |
| 6.3 | Configure Prometheus scraping | Prometheus auto-scrapes `/api/v1/metrics` | Already configured in `docker-compose.prod.yml` |

---

## 7. Backup Configuration (Optional)

| # | Action | .env Variable(s) | Notes |
|---|--------|-------------------|-------|
| 7.1 | Configure S3 backup target | `BACKUP_S3_UPLOAD_ENABLED=true`, `BACKUP_S3_ENDPOINT`, `BACKUP_S3_BUCKET`, `BACKUP_S3_REGION`, `BACKUP_S3_ACCESS_KEY`, `BACKUP_S3_SECRET_KEY` | Optional. Backups also work locally without S3 |
| 7.2 | Test backup/restore cycle | `./scripts/backup-db.ps1 -DryRun` then `./scripts/backup-db.ps1` | Creates a `pg_dump` archive. Restore with `./scripts/restore-db.ps1` |
| 7.3 | Set retention policy | `BACKUP_RETENTION_DAYS=30` | Automatic cleanup of old backups |

---

## 8. User Acceptance Testing

| # | Action | How |
|---|--------|-----|
| 8.1 | Upload real company documents | Create a case via the workbench, upload real P&L, contracts, MCA filings, etc. |
| 8.2 | Run full 7-step pipeline | Create case -> seed checklist -> upload docs -> scan issues -> review/approve -> execute run -> download export |
| 8.3 | Verify financial QoE extraction | Check that financial metrics, ratios, EBITDA adjustments are correctly parsed from real XLSX/PDF |
| 8.4 | Verify legal/tax/regulatory analysis | Check DIN extraction, contract clause detection, compliance matrix accuracy |
| 8.5 | Verify DOCX/PDF reports | Download export ZIP, open reports in Word/PDF viewer, verify formatting and content |
| 8.6 | Test with LLM enabled | Run workflow with LLM configured, compare CrewAI output quality vs deterministic fallback |

---

## 9. Security Review

| # | Action | How |
|---|--------|-----|
| 9.1 | Penetration test | Engage security team or use automated tools (OWASP ZAP, Burp Suite) against the running API |
| 9.2 | Dependency audit | `pip audit` for Python, `npm audit` for Node.js |
| 9.3 | Secret scanning | Verify no real credentials committed to git. Check `.env` is in `.gitignore` |
| 9.4 | Review auth flows | Verify JWT expiry, token refresh, role-based access controls |
| 9.5 | Compliance signoff | Document security posture for any regulatory requirements (DPDP 2025, SOC 2, etc.) |

---

## Quick Start (Minimum Viable Production)

The fastest path to a working production system:

1. Install Docker Desktop and start it
2. Copy `.env.example` to `.env`
3. Set: `JWT_SECRET` (32+ random bytes), `POSTGRES_PASSWORD` (strong), `MINIO_ROOT_PASSWORD` (strong)
4. Set: `LLM_PROVIDER=openai`, `LLM_API_KEY=<your-openrouter-key>`, `LLM_BASE_URL=https://openrouter.ai/api/v1`, `LLM_MODEL=openai/gpt-4o-mini`
5. Run: `docker compose -f docker-compose.prod.yml up -d`
6. Wait 30s for services to stabilize
7. Open `http://localhost:3000` for the workbench
8. Create a case and run the full pipeline

Everything else (connectors, observability, backups, security review) can be configured incrementally.
