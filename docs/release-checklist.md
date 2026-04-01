# Release Checklist

## Before Release

- `./scripts/check.ps1` passes
- `./scripts/generate-api-reference.ps1` passes and `docs/api-reference.md` is current
- `./scripts/backup-db.ps1 -DryRun` passes
- `docker compose -f docker-compose.prod.yml config` passes
- `./scripts/smoke.ps1 -UseJwt` passes against the running API
- latest evaluation artifact exists under `artifacts/evaluations/`
- latest load-benchmark artifact exists under `artifacts/evaluations/`
- regression baseline comparison passes
- credit-lending suite passes if that pack is in release scope
- vendor-onboarding suite passes if that pack is in release scope
- manufacturing / industrials suite passes if that sector pack is in release scope
- BFSI / NBFC suite passes if that sector pack is in release scope
- `GET /api/v1/health/readiness` returns `ok`
- `/status` shows expected dependency states and org-default LLM runtime
- auth mode is confirmed for the target environment and `JWT_SECRET` is not default
- default credentials are removed from shared environments
- `PHASE17_REQUIRE_LIVE_VALIDATION=true ./scripts/check.ps1` passes in the release environment
- `./scripts/validate-prod-stack.ps1 -RequireLive` passes in the release environment
- README and docs match the repo state

## Functional Checks

- create and inspect a case
- seed checklist items
- upload a document and verify evidence creation
- run issue scan and confirm no duplicate issue creation on rerun
- execute reviewer approval
- execute a workflow run and inspect report bundles
- generate a run export package and inspect the stored zip contents
- open the case and run views in the web workbench
- open `/status` and verify dependency refresh plus LLM default behavior
- verify report downloads, generated DOCX/PDF bundles, and API-reference docs remain aligned
