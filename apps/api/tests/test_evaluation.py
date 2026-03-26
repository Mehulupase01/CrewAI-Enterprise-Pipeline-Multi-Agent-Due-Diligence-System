from crewai_enterprise_pipeline_api.evaluation.scenarios import (
    CREDIT_LENDING_EXPANSION_SCENARIOS,
    EVALUATION_SUITES,
    PHASE5_FIRST_SLICE_SCENARIOS,
)


def test_evaluation_scenarios_are_unique_and_well_formed() -> None:
    scenario_codes: set[str] = set()

    for suite_key, scenarios in (
        ("phase5_first_slice", PHASE5_FIRST_SLICE_SCENARIOS),
        ("credit_lending_expansion", CREDIT_LENDING_EXPANSION_SCENARIOS),
    ):
        assert suite_key in EVALUATION_SUITES
        for scenario in scenarios:
            assert scenario.code not in scenario_codes
            scenario_codes.add(scenario.code)
            assert scenario.case_payload["country"] == "India"
            assert scenario.expectation.min_trace_events >= 6
            assert scenario.expectation.min_report_bundles >= 3
            assert scenario.expectation.min_syntheses >= 8
            assert scenario.approval_payload["reviewer"]
            assert scenario.run_payload["requested_by"]
            if suite_key == "phase5_first_slice":
                assert scenario.case_payload["motion_pack"] == "buy_side_diligence"
                assert scenario.case_payload["sector_pack"] == "tech_saas_services"
            if suite_key == "credit_lending_expansion":
                assert scenario.case_payload["motion_pack"] == "credit_lending"
            for upload in scenario.upload_documents:
                assert upload.filename
                assert upload.content.strip()
                assert upload.source_kind == "uploaded_dataroom"
