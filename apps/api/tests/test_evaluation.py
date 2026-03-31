from crewai_enterprise_pipeline_api.evaluation.scenarios import (
    BFSI_NBFC_EXPANSION_SCENARIOS,
    CREDIT_LENDING_EXPANSION_SCENARIOS,
    EVALUATION_SUITES,
    MANUFACTURING_INDUSTRIALS_EXPANSION_SCENARIOS,
    PHASE5_FIRST_SLICE_SCENARIOS,
    PHASE8_FINANCIAL_QOE_SCENARIOS,
    VENDOR_ONBOARDING_EXPANSION_SCENARIOS,
)


def test_evaluation_scenarios_are_unique_and_well_formed() -> None:
    scenario_codes: set[str] = set()

    for suite_key, scenarios in (
        ("phase5_first_slice", PHASE5_FIRST_SLICE_SCENARIOS),
        ("phase8_financial_qoe", PHASE8_FINANCIAL_QOE_SCENARIOS),
        ("credit_lending_expansion", CREDIT_LENDING_EXPANSION_SCENARIOS),
        ("vendor_onboarding_expansion", VENDOR_ONBOARDING_EXPANSION_SCENARIOS),
        (
            "manufacturing_industrials_expansion",
            MANUFACTURING_INDUSTRIALS_EXPANSION_SCENARIOS,
        ),
        ("bfsi_nbfc_expansion", BFSI_NBFC_EXPANSION_SCENARIOS),
    ):
        assert suite_key in EVALUATION_SUITES
        for scenario in scenarios:
            assert scenario.code not in scenario_codes
            scenario_codes.add(scenario.code)
            assert scenario.case_payload["country"] == "India"
            assert scenario.expectation.min_trace_events >= 6
            assert scenario.expectation.min_report_bundles >= 3
            assert scenario.expectation.min_syntheses >= 7
            assert scenario.approval_payload["reviewer"]
            assert scenario.run_payload["requested_by"]
            if suite_key == "phase5_first_slice":
                assert scenario.case_payload["motion_pack"] == "buy_side_diligence"
                assert scenario.case_payload["sector_pack"] == "tech_saas_services"
            if suite_key == "phase8_financial_qoe":
                assert scenario.financial_summary_expectation is not None
                assert scenario.case_payload["motion_pack"] == "credit_lending"
            if suite_key == "credit_lending_expansion":
                assert scenario.case_payload["motion_pack"] == "credit_lending"
            if suite_key == "vendor_onboarding_expansion":
                assert scenario.case_payload["motion_pack"] == "vendor_onboarding"
            if suite_key == "manufacturing_industrials_expansion":
                assert scenario.case_payload["sector_pack"] == "manufacturing_industrials"
            if suite_key == "bfsi_nbfc_expansion":
                assert scenario.case_payload["sector_pack"] == "bfsi_nbfc"
            for upload in scenario.upload_documents:
                assert upload.filename
                assert upload.content_bytes is not None or upload.content.strip()
                assert upload.source_kind == "uploaded_dataroom"
