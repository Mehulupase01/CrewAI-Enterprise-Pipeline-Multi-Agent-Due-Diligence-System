# CrewAI Enterprise Pipeline: India Due Diligence Operating System

## Abstract

This repository is the production build-out of an India-focused due diligence
operating system. It combines a FastAPI control plane, a Next.js analyst
workbench, CrewAI orchestration, structured evidence tracking, and a modular
pack model that lets the platform grow from buy-side M&A diligence into
credit/lending, vendor onboarding, manufacturing/industrials, and
fintech/NBFC/BFSI workflows.

## What We Are Building

This is not a toy "four agents and a PDF" demo. The target product is a real
internal diligence platform with:

- secure document ingestion and evidence normalization
- India-specific rule packs and workflow packs
- multi-workstream findings and flag management
- reviewer approvals and traceable report generation
- local-first infrastructure that is ready to harden for production

The first flagship slice targets:

- `BuySideDiligencePack`
- `TechSaaSServicesPack`
- India as the primary jurisdiction

The architecture is already shaped for later expansion into:

- `CreditLendingPack`
- `VendorOnboardingPack`
- `ManufacturingIndustrialsPack`
- `BFSINBFCPack`

## Repo Structure

```text
apps/
  api/        FastAPI control plane and CrewAI runtime
  web/        Next.js analyst workbench
docs/         Architecture and verification notes
scripts/      PowerShell bootstrap, dev, and check scripts
docker-compose.yml
```

## Current Phase

The repository has completed Phases 0-12 from the current master-plan execution
sequence. After Phase 7, the repo also received an additional CrewAI depth
enhancement: tool-grounded evidence access for the LLM path. Phase 8 is closed
as the canonical Financial Quality of Earnings (QoE) engine, Phase 9 is closed
as the canonical Legal / Tax / Regulatory engine, Phase 10 is closed as the
canonical Commercial / Operations / Cyber / Forensic engine, Phase 11 is
closed as the canonical Motion Pack Deepening layer, and Phase 12 is closed as
the canonical Sector Pack Deepening layer. The current build includes the first
flagship buy-side slice, all planned motion and sector expansions, analyst-ready
export archives, scoped CrewAI evidence tools, and workflow-integrated
financial, legal/compliance, Phase 10 domain-analysis, Phase 11 motion-pack
analysis, and Phase 12 sector-pack analysis layers on top of the existing
hardened platform spine:

- persisted case operations backed by SQLAlchemy
- document upload, parsing, storage, and evidence extraction
- issue register endpoints plus deterministic evidence-to-flag scanning
- pack-aware checklist seeding, item updates, and completeness coverage summaries
- approval review gate plus executive memo report preview endpoint
- persisted workflow runs with trace events and generated report bundles
- workstream synthesis for the first diligence slice
- structured financial workbook parsing into annual periods and QoE adjustments
- `GET /api/v1/cases/{case_id}/financial-summary` for normalized EBITDA,
  financial ratios, and red-flag analysis
- automatic checklist satisfaction for relevant financial workstream items
- CrewAI financial tools and sector benchmarks for the financial workstream and
  coordinator
- `GET /api/v1/cases/{case_id}/legal-summary` for directors, DINs,
  shareholding, subsidiary, charge, and contract-clause extraction
- `GET /api/v1/cases/{case_id}/tax-summary` for GSTIN extraction, tax-area
  statuses, and statutory flag analysis
- `GET /api/v1/cases/{case_id}/compliance-matrix` for sector-aware compliance
  matrix generation across MCA, licensing, and BFSI-specific RBI or SEBI regimes
- automatic checklist satisfaction for relevant legal, tax, and regulatory
  workstream items
- CrewAI compliance tools for legal, tax, regulatory, and coordinator agents
- `GET /api/v1/cases/{case_id}/commercial-summary` for customer concentration,
  NRR, churn, pricing-pressure, and renewal-risk analysis
- `GET /api/v1/cases/{case_id}/operations-summary` for supplier concentration,
  single-site dependency, and key-person risk analysis
- `GET /api/v1/cases/{case_id}/cyber-summary` for DPDP/privacy control review,
  certification posture, breach history, and analyst-readable cyber flags
- `GET /api/v1/cases/{case_id}/forensic-flags` for structured related-party,
  round-tripping, revenue-anomaly, and litigation flags
- automatic checklist satisfaction for relevant commercial, operations, cyber,
  and forensic workstream items
- CrewAI Phase 10 tools for commercial signals, operations risks, cyber
  controls, and forensic flags
- `GET /api/v1/cases/{case_id}/buy-side-analysis` for valuation bridge items,
  SPA issue tracking, and PMI risk analysis
- `GET /api/v1/cases/{case_id}/borrower-scorecard` for weighted credit section
  scoring, covenant tracking, and borrower rating
- `GET /api/v1/cases/{case_id}/vendor-risk-tier` for vendor tiering, scoring
  breakdown, certification requirements, and review cadence
- automatic checklist satisfaction for motion-pack-specific buy-side, credit,
  and vendor-onboarding items
- executive memo motion-pack highlights plus workflow-integrated motion-pack
  refresh across traces and syntheses
- CrewAI Phase 11 motion-pack specialist tools and prompts for buy-side,
  credit, and vendor review
- `GET /api/v1/cases/{case_id}/tech-saas-metrics` for ARR waterfall, NRR,
  churn, CAC, LTV, and payback analysis
- `GET /api/v1/cases/{case_id}/manufacturing-metrics` for capacity utilization,
  working-capital metrics, asset-register extraction, and plant/commercial risk
  flagging
- `GET /api/v1/cases/{case_id}/bfsi-nbfc-metrics` for GNPA, NNPA, CRAR, ALM,
  PSL posture, and bucket-gap analysis
- automatic checklist satisfaction for sector-pack-specific Tech/SaaS,
  Manufacturing, and BFSI/NBFC items
- executive memo sector-pack highlights plus workflow-integrated sector-pack
  refresh across traces and syntheses
- CrewAI Phase 12 sector-pack specialist tools and prompt snapshots for
  Tech/SaaS, Manufacturing, and BFSI/NBFC review
- tool-grounded CrewAI workstream analysis with scoped evidence, issue, and
  checklist review tools over pre-loaded case snapshots
- analyst workbench dashboard, case workspace, and run viewer with live API support
- document, evidence, request-list, and Q&A tracker endpoints
- source-adapter catalog for uploaded, public, and vendor-backed evidence
- deterministic evaluation scenarios with saved JSON scorecards
- a repeatable quality gate that exercises blocked, approved-clean, and
  approved-nonblocking-risk diligence runs
- run-level export-package generation that writes zip archives with markdown
  reports, manifest metadata, execution trace data, and JSON case snapshots
- role-based internal auth that can be enforced outside local dev and test
- request ID propagation plus a readiness endpoint for operations checks
- deployment, runbook, release-checklist, and smoke-check assets
- a supported `CreditLendingPack` with underwriting checklist templates,
  credit-risk heuristics, and motion-aware memo generation
- a supported `VendorOnboardingPack` with third-party onboarding templates,
  integrity-risk heuristics, and `Third-Party Risk Memo` generation
- a supported `ManufacturingIndustrialsPack` with sector-specific checklist
  templates for inventory quality, plant utilisation, supplier concentration,
  EHS and factory compliance, order-book review, and procurement leakage
- manufacturing-specific issue heuristics for environmental notices, inventory
  obsolescence, single-site dependence, and raw-material concentration
- a supported `BFSINBFCPack` with sector-specific checklist templates for asset
  quality, ALM and liquidity, RBI registration and returns, underwriting and
  collections governance, KYC or AML and data controls, and connected lending
- BFSI-specific issue heuristics for supervisory exposure, portfolio-quality
  deterioration, ALM stress, KYC or AML control weakness, connected lending or
  evergreening, and collections-outsourcing risk
- multi-suite evaluation coverage across buy-side, credit-lending,
  vendor-onboarding, manufacturing-enabled, and BFSI-enabled flows
- Dockerized local dependencies plus automated checks

## Local Development

### 1. Bootstrap the environment

The project uses a dedicated Conda environment named
`crewai-enterprise-pipeline`.

```powershell
./scripts/bootstrap.ps1
```

### 2. Start the local infrastructure

```powershell
./scripts/dev-stack.ps1
```

### 3. Run the API

```powershell
./scripts/dev-api.ps1
```

### 4. Run the web workbench

```powershell
./scripts/dev-web.ps1
```

## Verification

Run the current platform checks with:

```powershell
./scripts/check.ps1
```

`check.ps1` now also writes a fresh evaluation artifact under
`artifacts/evaluations/`.

To run the evaluation suite directly:

```powershell
./scripts/evaluate.ps1
```

To run only the credit-lending expansion suite:

```powershell
./scripts/evaluate.ps1 -Suite credit_lending_expansion
```

To run only the vendor-onboarding expansion suite:

```powershell
./scripts/evaluate.ps1 -Suite vendor_onboarding_expansion
```

To run only the manufacturing / industrials expansion suite:

```powershell
./scripts/evaluate.ps1 -Suite manufacturing_industrials_expansion
```

To run only the BFSI / NBFC expansion suite:

```powershell
./scripts/evaluate.ps1 -Suite bfsi_nbfc_expansion
```

To run only the Phase 8 financial QoE suite:

```powershell
./scripts/evaluate.ps1 -Suite phase8_financial_qoe
```

To run only the Phase 9 legal / tax / regulatory suite:

```powershell
./scripts/evaluate.ps1 -Suite phase9_legal_tax_regulatory
```

To run only the Phase 10 commercial / operations / cyber / forensic suite:

```powershell
./scripts/evaluate.ps1 -Suite phase10_commercial_operations_cyber_forensic
```

To run only the Phase 11 motion-pack deepening suite:

```powershell
./scripts/evaluate.ps1 -Suite phase11_motion_pack_deepening
```

To run only the Phase 12 sector-pack deepening suite:

```powershell
./scripts/evaluate.ps1 -Suite phase12_sector_pack_deepening
```

To run a live API smoke check after the stack is up:

```powershell
./scripts/smoke.ps1
```

Workflow runs can now also produce durable export packages through the API at:

```text
POST /api/v1/cases/{case_id}/runs/{run_id}/export-package
```

The project is only considered complete phase-by-phase when the code, tests,
docs, demo workflow, evaluation artifacts, and regression baseline all exist
together.

## Operations Docs

- `docs/deployment.md`
- `docs/runbook.md`
- `docs/release-checklist.md`
