# CrewAI Enterprise Pipeline: India Due Diligence Operating System

## Abstract

This repository is the production build-out of an India-focused due diligence
operating system. It combines a FastAPI control plane, a Next.js analyst
workbench, CrewAI orchestration, structured evidence tracking, and a modular
pack model that lets the platform grow from buy-side M&A diligence into
credit/lending, vendor onboarding, manufacturing/industrials, and future BFSI
workflows.

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

The repository has completed the third post-flagship expansion phase:
`ManufacturingIndustrialsPack` now runs alongside the existing motion-pack
expansions on the same hardened platform spine. The current build includes the
first flagship buy-side slice plus two additional motion packs and one
additional supported sector pack:

- persisted case operations backed by SQLAlchemy
- document upload, parsing, storage, and evidence extraction
- issue register endpoints plus deterministic evidence-to-flag scanning
- pack-aware checklist seeding, item updates, and completeness coverage summaries
- approval review gate plus executive memo report preview endpoint
- persisted workflow runs with trace events and generated report bundles
- workstream synthesis for the first diligence slice
- analyst workbench dashboard, case workspace, and run viewer with live API support
- document, evidence, request-list, and Q&A tracker endpoints
- source-adapter catalog for uploaded, public, and vendor-backed evidence
- deterministic evaluation scenarios with saved JSON scorecards
- a repeatable quality gate that exercises blocked, approved-clean, and
  approved-nonblocking-risk diligence runs
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
- multi-suite evaluation coverage across buy-side, credit-lending,
  vendor-onboarding, and manufacturing-enabled flows
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

To run a live API smoke check after the stack is up:

```powershell
./scripts/smoke.ps1
```

The project is only considered complete phase-by-phase when the code, tests,
docs, demo workflow, evaluation artifacts, and regression baseline all exist
together.

## Operations Docs

- `docs/deployment.md`
- `docs/runbook.md`
- `docs/release-checklist.md`
