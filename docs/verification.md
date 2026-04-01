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

The current gate now covers the foundation plus the implemented canonical engine layers through Phase 17, the completed custom Phase 19 runtime-control tranche, and the repo-side implementation of Phase 18 release packaging:

- backend app boot and schema lifecycle
- typed configuration loading
- persisted case workflow endpoints
- upload parsing, storage fallback, and evidence extraction
- issue-register creation and repeat-safe evidence scans
- checklist seeding, checklist updates, and completion coverage summaries
- approval review decisions and executive memo generation
- workflow run execution with trace events and generated report bundles
- durable run export-package generation with stored zip artifacts
- persisted workstream synthesis outputs per run
- tool-grounded CrewAI workstream analysis over pre-loaded evidence, issue, checklist, and chunk snapshots
- persisted tool-usage trace summaries for CrewAI workstream and coordinator runs
- structured financial workbook parsing and annual period normalization
- financial QoE adjustments, normalized EBITDA bridge, and ratio computation
- financial red-flag detection for concentration, cash conversion, leverage, coverage, seasonality, and growth quality
- automatic checklist satisfaction for financial workstream items
- dedicated Phase 8 financial QoE evaluation coverage
- structured legal summary generation for directors, DINs, shareholding, subsidiaries, charges, and contract clauses
- structured tax compliance summary generation for GST, income tax, TDS/payroll, transfer pricing, and deferred-tax signals
- sector-aware regulatory compliance matrix generation across MCA, licensing, and BFSI-specific RBI or SEBI regimes
- negation-aware tax and regulatory phrase matching to avoid false negatives from language like `no notice` or `no sanctions`
- automatic checklist satisfaction for legal, tax, and regulatory workstream items
- dedicated Phase 9 legal/tax/regulatory evaluation coverage
- structured commercial concentration, retention, pricing-pressure, and renewal-risk extraction
- structured operations dependency, supplier-concentration, single-site, and key-person analysis
- structured cyber/privacy control review with analyst-readable flags, certification posture, and breach-history extraction
- structured forensic related-party, round-tripping, revenue-anomaly, and litigation flag detection
- automatic checklist satisfaction for commercial, operations, cyber/privacy, and forensic workstream items
- dedicated Phase 10 commercial/operations/cyber/forensic evaluation coverage
- centralized motion-pack and sector-pack checklist composition with duplicate template-key protection
- structured buy-side valuation bridge, SPA issue matrix, and PMI risk generation
- structured borrower scorecard and covenant tracking generation for credit/lending motion packs
- structured vendor risk tiering, questionnaire generation, and certification tracking for vendor onboarding motion packs
- automatic checklist satisfaction for motion-pack-specific buy-side, credit, and vendor onboarding items
- workflow refresh, trace-event enrichment, synthesis updates, and executive memo highlights for motion-pack depth
- dedicated Phase 11 motion-pack deepening evaluation coverage
- structured Tech/SaaS ARR waterfall, MRR, NRR, churn, LTV, CAC, and payback extraction
- structured Manufacturing capacity, DIO/DSO/DPO, asset-turnover, and asset-register extraction
- structured BFSI / NBFC GNPA, NNPA, CRAR, ALM mismatch, PSL posture, and ALM bucket extraction
- automatic checklist satisfaction for sector-pack-specific Tech/SaaS, Manufacturing, and BFSI / NBFC items
- workflow refresh, trace-event enrichment, synthesis updates, executive memo highlights, and CrewAI tool surfaces for sector-pack depth
- dedicated Phase 12 sector-pack deepening evaluation coverage
- Jinja2-based rich report rendering for standard, lender, board memo, and one-pager templates
- markdown-first full-report and financial-annex generation
- DOCX generation from rendered markdown with cover page, TOC, section headings, lists, and tables
- PDF generation from rendered markdown with cover page, TOC, section headings, lists, and tables
- persisted report-template selection on workflow runs and rich report-bundle storage metadata
- report-bundle download endpoints for markdown and binary artifacts
- ZIP export-package inclusion of rich report markdown, DOCX, and PDF files
- dedicated Phase 13 rich-reporting evaluation coverage
- registered source-adapter catalog metadata with available/stub/unavailable status
- shared fetch-and-ingest support for MCA21, GSTIN, SEBI SCORES, RoC filings, CIBIL stub, and sanctions/watchlist adapters
- connector payload ingestion through the shared artifact storage, chunking, evidence extraction, and entity-extraction pipeline
- dedicated Phase 14 India connector evaluation coverage
- JWT bearer auth for non-dev environments plus dev/test header-auth compatibility
- seeded organization and API-client bootstrap for fresh or migrated databases
- session-scoped org isolation across tenant-scoped ORM models
- admin audit-log access plus auth-failure and mutation audit coverage
- rate limiting with Redis-first behavior and deterministic in-memory fallback
- structured logging via `structlog` with production JSON mode and bound request context
- OpenTelemetry initialization for FastAPI, SQLAlchemy, and HTTPX
- Prometheus metrics exposure through `GET /api/v1/metrics`
- root liveness/readiness endpoints through `GET /api/v1/health/liveness` and `GET /api/v1/health/readiness`
- dependency readiness evaluation for database, Redis, storage, OpenRouter/provider state, and registered source adapters
- observability Docker stack configuration for Prometheus, Grafana, and Tempo
- persisted dependency snapshot refresh and retrieval for runtime-status surfaces
- OpenRouter model-catalog discovery with capability filtering and cache behavior
- org-scoped default LLM runtime config plus per-run provider/model overrides
- workflow-run persistence of effective LLM provider/model across sync and queued execution paths
- admin dependency refresh and runtime-control endpoints
- `/status` workbench data wiring and run-detail runtime display
- 30 end-to-end evaluation scenarios across 13 suites, including the Phase 17 matrix/red-team coverage
- per-scenario quality scorecards plus suite-level and combined quality summaries
- committed regression-baseline comparison against `artifacts/baselines/all-supported-suites-baseline.json`
- in-process ASGI load benchmark for `GET /system/health`, `POST /issues/scan`, and `POST /search`
- optional live OpenRouter benchmark and live connector validation suites with explicit skip-vs-fail behavior
- generated API-reference docs from the live OpenAPI schema
- backup dry-run automation and restore dry-run planning
- production compose config validation for `docker-compose.prod.yml`
- full Next.js production build in the standard repo gate
- optional live production-stack validation through `scripts/validate-prod-stack.ps1`
- deterministic end-to-end evaluation scenarios with saved JSON scorecards
- repeat-scan regression checks for issue fingerprint reuse
- enforced-auth and role-guard tests
- request ID propagation on API responses
- readiness endpoint coverage
- credit-lending checklist, memo, and evaluation coverage
- vendor-onboarding checklist, memo, and evaluation coverage
- manufacturing / industrials checklist composition, issue-heuristic, and
  evaluation coverage
- BFSI / NBFC checklist composition, issue-heuristic, and evaluation coverage
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
- A workflow run can be exported into a durable archive package with manifest,
  markdown bundles, and JSON snapshots.
- A run produces durable workstream syntheses for the first diligence domains.
- When CrewAI is active, agent runs can drill into scoped evidence, issue, and
  checklist tools without breaking the deterministic fallback path.
- The API can build a financial summary from uploaded workbooks, including
  normalized EBITDA, core ratios, and financial diligence flags.
- Financial summaries can auto-satisfy relevant checklist items and that state
  is reflected in workflow coverage, approvals, and report generation.
- The API can build a legal summary from uploaded documents, including DIN,
  shareholding, subsidiary, charge, and contract-clause extraction.
- The API can build a tax summary from uploaded documents, including GSTIN
  extraction, tax-area statuses, and checklist auto-satisfaction.
- The API can build a sector-aware compliance matrix from uploaded documents,
  including MCA and BFSI-style RBI or SEBI compliance statuses.
- Legal, tax, and regulatory summaries must refresh inside workflow runs and
  enrich trace events, syntheses, reports, and CrewAI tool surfaces consistently.
- The API can build commercial summaries from uploaded documents, including
  concentration signals, NRR, churn, pricing-pressure, and renewal-risk flags.
- The API can build operations summaries from uploaded documents, including
  supplier concentration, single-site dependency, key-person dependency, and
  continuity-risk flags.
- The API can build cyber/privacy summaries from uploaded documents, including
  DPDP/security control states, certification posture, incident history, and
  analyst-readable cyber flags.
- The API can build forensic summaries from uploaded documents, including
  related-party, round-tripping, revenue-anomaly, and litigation flags.
- Phase 10 summaries must refresh inside workflow runs and enrich trace events,
  syntheses, reports, and CrewAI tool surfaces consistently.
- The API can build a structured buy-side analysis from uploaded evidence,
  including valuation bridge items, SPA issue tracking, and PMI risks.
- The API can build a structured borrower scorecard from uploaded evidence,
  including covenant tracking, weighted section scores, and overall rating.
- The API can build a structured vendor risk tier from uploaded evidence,
  including score breakdown, questionnaire outputs, certification requirements,
  and next-review guidance.
- Phase 11 motion-pack outputs must refresh inside workflow runs and enrich
  trace events, syntheses, reports, and CrewAI tool surfaces consistently.
- The API can build structured Tech/SaaS metrics from uploaded evidence,
  including ARR waterfall, MRR, NRR, churn, LTV, CAC, payback, and sector flags.
- The API can build structured Manufacturing metrics from uploaded evidence,
  including capacity utilization, DIO/DSO/DPO, asset turnover, asset register,
  and plant/commercial/regulatory sector flags.
- The API can build structured BFSI / NBFC metrics from uploaded evidence,
  including GNPA, NNPA, CRAR, ALM mismatch, PSL posture, ALM buckets, and
  analyst-readable sector flags.
- Phase 12 sector-pack outputs must refresh inside workflow runs and enrich
  trace events, syntheses, reports, and CrewAI tool surfaces consistently.
- The API can render full reports and financial annexes in markdown for
  multiple templates, including standard, lender, board memo, and one-pager
  outputs.
- Workflow runs can persist the chosen report template and generate matching
  markdown, DOCX, and PDF report bundles as durable run artifacts.
- Report bundles can be downloaded individually through the API and included
  in export-package ZIP archives without regeneration drift.
- The API exposes a registered source-adapter catalog with connector status,
  credential requirements, fetch capability, and default evidence metadata.
- The API can fetch and ingest connector-backed evidence into a case through
  `POST /api/v1/cases/{case_id}/source-adapters/{adapter_id}/fetch`.
- Connector-fetched evidence lands in the same artifact, chunk, and evidence
  pipeline used for uploaded files so downstream domain engines can consume it.
- The API can issue JWT bearer tokens through `POST /api/v1/auth/token` using
  DB-backed API clients.
- Tenant-scoped records are isolated by org, and callers from one org cannot
  read or mutate another org's cases through standard non-admin paths.
- The API records audit entries for successful mutations, token issuance, and
  authorization failures, and exposes admin audit-log retrieval.
- Rate limiting applies across auth, connector, mutating, and read routes
  without making Redis a hard requirement for local verification.
- The first-slice evaluation suite passes blocked, clean-approved, and
  approved-nonblocking-risk scenarios.
- Every quality-gate run writes a machine-readable artifact under
  `artifacts/evaluations/`.
- Secured routes reject missing or under-privileged callers when auth is enforced.
- The API returns a request ID header on responses.
- The API persists the latest dependency snapshot and exposes it through read and admin refresh surfaces without inventing a separate health model.
- The API can resolve LLM runtime in a strict order: per-run override, org default, environment fallback, then deterministic fallback when no explicit live provider is requested.
- Explicitly requested unavailable live runtimes fail fast with `503` instead of silently degrading to deterministic execution.
- Queued workflow runs preserve the effective provider/model chosen at enqueue time so worker execution cannot drift from the initiating request.
- The repo evaluation corpus covers at least 30 scenarios and every active `motion_pack x sector_pack` combination.
- Evaluation output includes quality scorecards and a committed regression baseline that the repo gate compares automatically.
- The load benchmark must pass the current local thresholds for core GET, issue scan, and search endpoints with zero request errors.
- Optional live OpenRouter and connector validation suites must report honest skips when credentials are absent and hard failures when strict live validation is requested.
- The repo must be able to regenerate `docs/api-reference.md` from the FastAPI OpenAPI schema without manual editing.
- The backup and restore scripts must support dry-run planning without requiring live database access.
- `docker compose -f docker-compose.prod.yml config` must succeed as part of the normal gate.
- The Next.js workbench must complete a production `npm run build`.
- Live production-stack validation must skip honestly when Docker is unavailable and become a hard failure when strict validation is required.
- The repo includes deployment, runbook, smoke-check, and release-checklist assets.
- The evaluation runner passes all supported suites, including credit lending,
  vendor onboarding, manufacturing / industrials, BFSI / NBFC, the dedicated
  Phase 9 legal/tax/regulatory suite, and the dedicated Phase 10
  commercial/operations/cyber/forensic suite, the dedicated Phase 11
  motion-pack deepening suite, the dedicated Phase 12 sector-pack
  deepening suite, the dedicated Phase 13 rich-reporting suite, and the
  dedicated Phase 14 India connector suite.
- The web app exposes a dashboard, case workspace, and run viewer over the shared case model.
- The workbench reflects the actual platform surface instead of generator boilerplate.
- The repo contains reproducible scripts for bootstrap, dev, and checks.
- Docker Compose starts the local backing services cleanly.
