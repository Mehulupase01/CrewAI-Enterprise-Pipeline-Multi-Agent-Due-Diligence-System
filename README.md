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

The repository is currently in `Phase 0 / Phase 1` foundation work:

- repo structure and conventions
- backend control-plane skeleton
- web workbench shell
- Dockerized local dependencies
- initial tests and verification scripts

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

Run the foundation checks with:

```powershell
./scripts/check.ps1
```

The project is only considered complete phase-by-phase when the code, tests,
docs, demo workflow, and regression baseline all exist together.
