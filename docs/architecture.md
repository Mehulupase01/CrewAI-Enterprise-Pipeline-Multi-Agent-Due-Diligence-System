# Architecture Overview

## Foundation Direction

The platform is being built as an India due diligence operating system with a
pack-based architecture. The goal is to keep the first production slice narrow
enough to verify, while avoiding hard-coding assumptions that would block later
credit, vendor, or sector expansions.

## Core Layers

### 1. Control Plane

The FastAPI service owns universal platform concepts:

- cases
- entities and counterparties
- documents and evidence
- findings and issues
- approvals
- report bundles
- run traces and cost ledgers

The first persisted platform entities are now live in the API surface:

- `Case`
- `ChecklistItem`
- `DocumentArtifact`
- `EvidenceNode`
- `IssueRegisterItem`
- `ApprovalDecision`
- `WorkflowRun`
- `RunTraceEvent`
- `ReportBundle`
- `WorkstreamSynthesis`
- `RequestItem`
- `QaItem`

### 2. Orchestration Layer

CrewAI Flows will coordinate agentic workflows, but the platform will not rely
on prompts for deterministic responsibilities. The control plane remains the
source of truth for:

- evidence provenance
- pack selection
- issue state
- approvals
- compliance coverage

### 3. Workbench

The Next.js app is the analyst and reviewer surface. It will eventually expose:

- case intake
- evidence review
- request-list and Q&A operations
- flags and issue heatmaps
- approval workflows
- report export

The first interface slice now includes:

- dashboard-level case overview
- detailed case workspace pages
- run-detail views for traces, syntheses, and report bundles
- live API loading with a safe local demo fallback

### 4. Platform Infrastructure

The local-first dev stack uses:

- PostgreSQL for the transactional store
- Redis for background coordination and caching
- MinIO-compatible object storage for document artifacts

## Pack Model

### Motion Packs

- `buy_side_diligence`
- `credit_lending`
- `vendor_onboarding`

### Sector Packs

- `tech_saas_services`
- `manufacturing_industrials`
- `bfsi_nbfc`

### Rule Packs

Rule packs capture jurisdictional and domain requirements such as:

- MCA / corporate records
- SEBI / listed entity obligations
- RBI / FEMA / FDI
- CCI combinations
- GST and direct tax
- labour and privacy

The first implementation slice only activates the buy-side + tech/service path,
but the contracts already account for later packs.

## Phase 2 Additions

The current implementation pass adds the first true operations layer:

- SQLAlchemy persistence with startup schema creation for local development
- case CRUD entry points and detail views
- document upload, parsing, storage fallback, and artifact registration
- evidence ledger entries tied to workstream domains
- issue-register records tied back to evidence with deterministic scan heuristics
- checklist template seeding, item status updates, and coverage summaries
- approval reviews and executive memo generation from structured case state
- persisted workflow runs with trace events and bundle generation
- workstream synthesis records for domain-level diligence views
- request-list and management Q&A tracking
- source-adapter contracts for uploaded, public, and vendor-driven evidence

## Phase 5 Additions

The first quality-gate layer is now part of the product:

- a deterministic evaluation harness that runs end-to-end against the live API
- named diligence scenarios for blocked-tax, clean-approved, and
  nonblocking-commercial-risk cases
- isolated temporary databases and storage roots for repeatable evaluation runs
- saved JSON scorecards under `artifacts/evaluations/`
- tighter repo verification so `scripts/check.ps1` now includes the evaluation
  suite in addition to lint, tests, and web checks
