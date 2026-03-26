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

The currently supported platform surface activates these pack combinations:

- `buy_side_diligence` + `tech_saas_services`
- `credit_lending` + `tech_saas_services`
- `vendor_onboarding` + `tech_saas_services`
- manufacturing / industrials as an active sector pack over supported motion packs
- `bfsi_nbfc` as an active sector pack over supported motion packs

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

## Phase 6 Additions

The first hardening layer is now in place:

- internal role-aware auth that can be enforced in production-shaped
  environments while keeping local development friction low
- request ID middleware for basic request correlation across API calls
- readiness reporting that validates database access and surfaces the latest
  evaluation baseline
- operations assets covering deployment, runbook steps, smoke checks, and
  release criteria

## Expansion Phase 1: Credit Lending

The first expansion pack is now implemented:

- `credit_lending` now seeds underwriting-specific checklist templates
- report generation is motion-aware and emits a `Credit Memo` instead of
  reusing buy-side wording
- issue heuristics now catch covenant stress, fund diversion, and collateral
  perfection gaps
- evaluation is suite-based, so the repo can grow from one flagship slice into
  multiple supported operating modes without losing repeatability

## Expansion Phase 2: Vendor Onboarding

The second expansion pack is now implemented:

- `vendor_onboarding` now seeds third-party onboarding and integrity checklist
  templates
- report generation emits a `Third-Party Risk Memo` with onboarding-specific
  summary and action language
- issue heuristics now catch sanctions, watchlist, and anti-bribery risk
  signals
- the evaluation harness now exercises all three supported motion packs under
  one repeatable quality gate

## Expansion Phase 3: Manufacturing / Industrials

The third expansion pack is now implemented:

- `manufacturing_industrials` now seeds sector-specific checklist templates for
  inventory quality, plant utilisation, supplier concentration, EHS or factory
  compliance, order-book review, and procurement leakage
- issue heuristics now detect environmental and factory-compliance exposure,
  inventory aging or obsolescence, single-site capacity dependence, and
  supplier or raw-material concentration
- the evaluation harness now proves that the manufacturing sector pack works
  both on the flagship buy-side flow and in composition with the
  `credit_lending` motion pack

## Expansion Phase 4: Fintech / NBFC / BFSI

The fourth expansion pack is now implemented:

- `bfsi_nbfc` now seeds sector-specific checklist templates for asset quality,
  ALM and liquidity, RBI registration and returns, underwriting and
  collections governance, KYC or AML and data controls, and connected lending
- issue heuristics now detect supervisory exposure, portfolio-quality
  deterioration, ALM mismatch, KYC or AML control weakness, connected lending
  or evergreening, and collections-outsourcing risk
- the evaluation harness now proves that the BFSI sector pack works both on
  the flagship buy-side flow and in composition with the `credit_lending`
  motion pack

## Post-Roadmap Enhancement 1: Run Export Packages

The first post-roadmap enhancement adds durable report delivery:

- workflow runs can now generate a persisted zip export package
- export archives include a manifest, markdown report bundles, run-trace data,
  workstream-synthesis data, and optional JSON case snapshots
- export artifacts are stored through the existing storage abstraction so they
  work in local storage or S3-compatible object storage
