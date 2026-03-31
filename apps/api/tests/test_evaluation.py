from crewai_enterprise_pipeline_api.evaluation.scenarios import (
    BFSI_NBFC_EXPANSION_SCENARIOS,
    CREDIT_LENDING_EXPANSION_SCENARIOS,
    EVALUATION_SUITES,
    MANUFACTURING_INDUSTRIALS_EXPANSION_SCENARIOS,
    PHASE5_FIRST_SLICE_SCENARIOS,
    PHASE8_FINANCIAL_QOE_SCENARIOS,
    PHASE9_LEGAL_TAX_REGULATORY_SCENARIOS,
    PHASE10_COMMERCIAL_OPERATIONS_CYBER_FORENSIC_SCENARIOS,
    PHASE11_MOTION_PACK_DEEPENING_SCENARIOS,
    PHASE12_SECTOR_PACK_DEEPENING_SCENARIOS,
    PHASE13_RICH_REPORTING_SCENARIOS,
    VENDOR_ONBOARDING_EXPANSION_SCENARIOS,
)


def test_evaluation_scenarios_are_unique_and_well_formed() -> None:
    scenario_codes: set[str] = set()

    for suite_key, scenarios in (
        ("phase13_rich_reporting", PHASE13_RICH_REPORTING_SCENARIOS),
        ("phase5_first_slice", PHASE5_FIRST_SLICE_SCENARIOS),
        ("phase8_financial_qoe", PHASE8_FINANCIAL_QOE_SCENARIOS),
        ("phase9_legal_tax_regulatory", PHASE9_LEGAL_TAX_REGULATORY_SCENARIOS),
        (
            "phase10_commercial_operations_cyber_forensic",
            PHASE10_COMMERCIAL_OPERATIONS_CYBER_FORENSIC_SCENARIOS,
        ),
        ("phase11_motion_pack_deepening", PHASE11_MOTION_PACK_DEEPENING_SCENARIOS),
        ("phase12_sector_pack_deepening", PHASE12_SECTOR_PACK_DEEPENING_SCENARIOS),
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
            if suite_key == "phase9_legal_tax_regulatory":
                assert scenario.legal_summary_expectation is not None
                assert scenario.tax_summary_expectation is not None
                assert scenario.compliance_matrix_expectation is not None
                assert scenario.case_payload["sector_pack"] == "bfsi_nbfc"
            if suite_key == "phase10_commercial_operations_cyber_forensic":
                assert scenario.commercial_summary_expectation is not None
                assert scenario.operations_summary_expectation is not None
                assert scenario.cyber_summary_expectation is not None
                assert scenario.forensic_summary_expectation is not None
            if suite_key == "phase11_motion_pack_deepening":
                assert (
                    scenario.buy_side_analysis_expectation is not None
                    or scenario.borrower_scorecard_expectation is not None
                    or scenario.vendor_risk_tier_expectation is not None
                )
            if suite_key == "phase12_sector_pack_deepening":
                assert (
                    scenario.tech_saas_metrics_expectation is not None
                    or scenario.manufacturing_metrics_expectation is not None
                    or scenario.bfsi_nbfc_metrics_expectation is not None
                )
            if suite_key == "phase13_rich_reporting":
                assert scenario.rich_reporting_expectation is not None
                assert scenario.run_payload["report_template"] == "board_memo"
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
