Run the full test and verification suite for this project.

Steps:
1. Run Python linting: `cd apps/api && python -m ruff check src tests`
2. Run Python tests: `cd apps/api && python -m pytest -v`
3. Run evaluation suites: `cd apps/api && python -m crewai_enterprise_pipeline_api.evaluation.runner --output-dir ../../artifacts/evaluations --suite all`
4. Run web linting: `cd apps/web && npm run lint`
5. Run web type checking: `cd apps/web && npm run typecheck`
6. Report results: number of tests passed/failed, evaluation scenario pass rate, any lint or type errors.

If a specific area is failing, dig into the failure and suggest fixes. Do not just report "tests failed" -- show which tests and why.

To run only a specific test: `cd apps/api && python -m pytest tests/test_cases.py -k "test_name" -v`

To run a single evaluation suite: `cd apps/api && python -m crewai_enterprise_pipeline_api.evaluation.runner --output-dir ../../artifacts/evaluations --suite <suite_name>`

Suite names: phase5_first_slice, credit_lending_expansion, vendor_onboarding_expansion, manufacturing_industrials_expansion, bfsi_nbfc_expansion.
