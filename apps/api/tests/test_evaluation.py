from crewai_enterprise_pipeline_api.evaluation.scenarios import (
    PHASE5_FIRST_SLICE_SCENARIOS,
)


def test_phase5_scenarios_are_unique_and_well_formed() -> None:
    scenario_codes: set[str] = set()

    for scenario in PHASE5_FIRST_SLICE_SCENARIOS:
        assert scenario.code not in scenario_codes
        scenario_codes.add(scenario.code)
        assert scenario.case_payload["motion_pack"] == "buy_side_diligence"
        assert scenario.case_payload["sector_pack"] == "tech_saas_services"
        assert scenario.expectation.min_trace_events >= 6
        assert scenario.expectation.min_report_bundles >= 3
        assert scenario.expectation.min_syntheses >= 8
        assert scenario.approval_payload["reviewer"]
        assert scenario.run_payload["requested_by"]
        for upload in scenario.upload_documents:
            assert upload.filename
            assert upload.content.strip()
            assert upload.source_kind == "uploaded_dataroom"
