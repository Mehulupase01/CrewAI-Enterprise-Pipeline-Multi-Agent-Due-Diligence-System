# CrewAI Enterprise Pipeline: India Due Diligence Operating System

## Abstract

This repository is the production build-out of an India-focused due diligence
operating system. It combines a FastAPI control plane, a Next.js analyst
workbench, CrewAI orchestration, structured evidence tracking, and a modular
pack model that lets the platform grow from buy-side M&A diligence into future
credit/lending, vendor onboarding, manufacturing, and BFSI workflows.

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

The repository has completed the first deterministic `Phase 3` slice and is
moving into deeper interface and workflow expansion:

- persisted case operations backed by SQLAlchemy
- document upload, parsing, storage, and evidence extraction
- issue register endpoints plus deterministic evidence-to-flag scanning
- pack-aware checklist seeding, item updates, and completeness coverage summaries
- approval review gate plus executive memo report preview endpoint
- persisted workflow runs with trace events and generated report bundles
- workstream synthesis for the first diligence slice
- document, evidence, request-list, and Q&A tracker endpoints
- source-adapter catalog for uploaded, public, and vendor-backed evidence
- analyst workbench dashboard aligned to the live platform surface
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

The project is only considered complete phase-by-phase when the code, tests,
docs, demo workflow, and regression baseline all exist together.
