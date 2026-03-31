from __future__ import annotations

from dataclasses import dataclass

from crewai_enterprise_pipeline_api.domain.models import MotionPack, SectorPack, WorkstreamDomain


@dataclass(frozen=True)
class ChecklistTemplateItem:
    template_key: str
    title: str
    detail: str
    workstream_domain: WorkstreamDomain
    mandatory: bool = True
    evidence_required: bool = True


def _item(
    template_key: str,
    title: str,
    detail: str,
    workstream_domain: WorkstreamDomain,
    *,
    mandatory: bool = True,
    evidence_required: bool = True,
) -> ChecklistTemplateItem:
    return ChecklistTemplateItem(
        template_key=template_key,
        title=title,
        detail=detail,
        workstream_domain=workstream_domain,
        mandatory=mandatory,
        evidence_required=evidence_required,
    )


BUY_SIDE_TEMPLATE: tuple[ChecklistTemplateItem, ...] = (
    _item(
        "financial_qoe.audited_financials",
        "Collect audited financial statements for the last five years",
        (
            "Validate annual income statement, balance sheet, and cash flow coverage, "
            "including auditor notes and management adjustments."
        ),
        WorkstreamDomain.FINANCIAL_QOE,
    ),
    _item(
        "financial_qoe.monthly_bridge",
        "Obtain monthly revenue and margin bridge",
        (
            "Reconcile monthly revenue, gross margin, deferred revenue, and churn "
            "drivers to annual reported performance."
        ),
        WorkstreamDomain.FINANCIAL_QOE,
    ),
    _item(
        "financial_qoe.revenue_recognition_policy",
        "Review revenue-recognition policy and contract cut-off testing",
        (
            "Inspect revenue-recognition policy, contract acceptance milestones, credit notes, "
            "and quarter-end cut-off patterns for premature recognition risk."
        ),
        WorkstreamDomain.FINANCIAL_QOE,
    ),
    _item(
        "financial_qoe.qoe_adjustment_register",
        "Build normalized EBITDA adjustment register",
        (
            "Separate one-off, owner-related, non-recurring, and run-rate adjustments into a "
            "signed-off QoE bridge with evidence support."
        ),
        WorkstreamDomain.FINANCIAL_QOE,
    ),
    _item(
        "financial_qoe.valuation_bridge",
        "Prepare valuation bridge from reported EBITDA to deal model assumptions",
        (
            "Link reported EBITDA, normalized EBITDA, working-capital normalization, net debt, "
            "and any purchase-price adjustments into a documented valuation bridge."
        ),
        WorkstreamDomain.FINANCIAL_QOE,
    ),
    _item(
        "financial_qoe.working_capital_peg",
        "Analyze normalized working-capital peg",
        (
            "Build monthly working-capital analysis, identify seasonality, and recommend a "
            "defensible peg for SPA negotiation."
        ),
        WorkstreamDomain.FINANCIAL_QOE,
    ),
    _item(
        "financial_qoe.net_debt_bridge",
        "Prepare net debt and debt-like items bridge",
        (
            "Reconcile cash, debt, leases, guarantees, deferred consideration, unpaid taxes, "
            "and other debt-like items relevant to closing."
        ),
        WorkstreamDomain.FINANCIAL_QOE,
    ),
    _item(
        "financial_qoe.cash_conversion_analysis",
        "Assess cash conversion and quality of earnings",
        (
            "Compare EBITDA to operating cash flow, identify receivable build, deferred revenue "
            "movements, and unusual working-capital leakage."
        ),
        WorkstreamDomain.FINANCIAL_QOE,
    ),
    _item(
        "financial_qoe.customer_margin_waterfall",
        "Review customer and product margin waterfalls",
        (
            "Test margin quality by customer, product, geography, and implementation cohort to "
            "identify hidden loss-making segments."
        ),
        WorkstreamDomain.FINANCIAL_QOE,
        mandatory=False,
    ),
    _item(
        "financial_qoe.forecast_vs_actual",
        "Compare budget, forecast, and actual performance",
        (
            "Assess management forecast credibility using historical miss patterns, pipeline "
            "conversion, and margin-delivery variance."
        ),
        WorkstreamDomain.FINANCIAL_QOE,
    ),
    _item(
        "financial_qoe.capex_maintenance_vs_growth",
        "Split maintenance versus growth capex",
        (
            "Classify historical capex, check capitalization policy, and assess whether EBITDA "
            "or free-cash-flow quality is overstated."
        ),
        WorkstreamDomain.FINANCIAL_QOE,
        mandatory=False,
    ),
    _item(
        "financial_qoe.related_party_financial_flows",
        "Trace related-party balances through the QoE lens",
        (
            "Reconcile related-party revenue, expenses, balances, and settlements to verify "
            "normalized earnings and leakage exposure."
        ),
        WorkstreamDomain.FINANCIAL_QOE,
    ),
    _item(
        "legal_corporate.cap_table",
        "Validate cap table and corporate actions",
        (
            "Review share issuances, transfers, ESOP pool, shareholder rights, and "
            "board or shareholder approvals."
        ),
        WorkstreamDomain.LEGAL_CORPORATE,
    ),
    _item(
        "legal_corporate.material_contracts",
        "Review material customer, vendor, and financing contracts",
        (
            "Check change-of-control clauses, termination rights, pricing protections, "
            "non-competes, and assignment restrictions."
        ),
        WorkstreamDomain.LEGAL_CORPORATE,
    ),
    _item(
        "legal_corporate.spa_issue_matrix",
        "Prepare SPA issue matrix and negotiation hotspots",
        (
            "Map diligence issues to SPA asks such as indemnities, escrows, holdbacks, "
            "conditions precedent, disclosure-letter qualifications, and covenant protections."
        ),
        WorkstreamDomain.LEGAL_CORPORATE,
    ),
    _item(
        "legal_corporate.corporate_actions_register",
        "Reconcile corporate-actions register",
        (
            "Validate board, committee, and shareholder approvals for key issuances, borrowings, "
            "guarantees, ESOP grants, and intercompany arrangements."
        ),
        WorkstreamDomain.LEGAL_CORPORATE,
    ),
    _item(
        "legal_corporate.ip_chain_of_title",
        "Verify IP ownership and assignment chain",
        (
            "Confirm that source code, trademarks, patents, domain names, and contractor-created "
            "IP are properly assigned to the target."
        ),
        WorkstreamDomain.LEGAL_CORPORATE,
    ),
    _item(
        "legal_corporate.employment_restrictions",
        "Review employment restrictions and change-in-control terms",
        (
            "Check key employment agreements, restrictive covenants, retention terms, severance, "
            "and change-in-control triggers."
        ),
        WorkstreamDomain.LEGAL_CORPORATE,
        mandatory=False,
    ),
    _item(
        "legal_corporate.litigation_schedule",
        "Assemble litigation and claims schedule",
        (
            "Collect ongoing claims, threatened disputes, settlement history, and legal counsel "
            "assessment of likely exposure."
        ),
        WorkstreamDomain.LEGAL_CORPORATE,
    ),
    _item(
        "legal_corporate.subsidiary_and_branch_structure",
        "Map subsidiary, branch, and step-down structure",
        (
            "Validate the legal-entity perimeter, dormant entities, branch offices, and any "
            "cross-border vehicles relevant to the transaction."
        ),
        WorkstreamDomain.LEGAL_CORPORATE,
        mandatory=False,
    ),
    _item(
        "legal_corporate.insurance_coverage_review",
        "Review insurance coverage and historic claims",
        (
            "Assess D&O, cyber, property, business interruption, E&O, and other material "
            "insurance coverage for gaps and claims history."
        ),
        WorkstreamDomain.LEGAL_CORPORATE,
        mandatory=False,
    ),
    _item(
        "tax.notice_register",
        "Reconcile direct and indirect tax exposures",
        (
            "Collect GST, TDS, income-tax filings, notices, demands, and payment "
            "history across relevant entities and states."
        ),
        WorkstreamDomain.TAX,
    ),
    _item(
        "tax.gst_reconciliation_pack",
        "Build GST reconciliation pack",
        (
            "Reconcile outward supplies, input tax credit, e-invoicing, e-way bills, and state "
            "registrations against filed returns and books."
        ),
        WorkstreamDomain.TAX,
    ),
    _item(
        "tax.direct_tax_assessment_status",
        "Review direct-tax assessment status",
        (
            "Check scrutiny assessments, appeals, advance-tax behavior, tax positions, and open "
            "direct-tax exposures over the diligence period."
        ),
        WorkstreamDomain.TAX,
    ),
    _item(
        "tax.withholding_and_payroll_status",
        "Review withholding-tax and payroll compliance",
        (
            "Validate TDS, PF, ESI, gratuity, bonus, and payroll tax posture, including notices "
            "and historical defaults."
        ),
        WorkstreamDomain.TAX,
    ),
    _item(
        "tax.transfer_pricing_support",
        "Review transfer-pricing policy and support",
        (
            "Collect TP studies, intercompany agreements, benchmarking, and audit history for "
            "domestic and cross-border related-party arrangements."
        ),
        WorkstreamDomain.TAX,
    ),
    _item(
        "tax.deferred_tax_and_attribute_review",
        "Assess deferred-tax assets and tax attributes",
        (
            "Review deferred-tax recoverability, MAT credits, losses, and incentives relevant to "
            "valuation, SPA drafting, and post-close tax planning."
        ),
        WorkstreamDomain.TAX,
        mandatory=False,
    ),
    _item(
        "regulatory.mca_consistency",
        "Validate MCA and statutory filing consistency",
        (
            "Confirm directors, charges, registered office data, and annual filings "
            "match management disclosures."
        ),
        WorkstreamDomain.REGULATORY,
    ),
    _item(
        "regulatory.license_and_permit_register",
        "Compile license and permit register",
        (
            "Catalog material licences, registrations, permits, renewals, and expiry dates across "
            "the target perimeter and operating locations."
        ),
        WorkstreamDomain.REGULATORY,
    ),
    _item(
        "regulatory.fema_fdi_screen",
        "Review FEMA, FDI, and cross-border compliance",
        (
            "Assess foreign shareholding, pricing compliance, reporting, downstream investments, "
            "and sectoral restrictions affecting ownership or future transfers."
        ),
        WorkstreamDomain.REGULATORY,
    ),
    _item(
        "regulatory.cci_threshold_screen",
        "Screen CCI combination and competition risk",
        (
            "Assess whether transaction thresholds, market overlaps, or customer concentration "
            "create any combination-notification or competition-law considerations."
        ),
        WorkstreamDomain.REGULATORY,
        mandatory=False,
    ),
    _item(
        "regulatory.privacy_and_sectoral_obligations",
        "Assess privacy and sectoral regulatory obligations",
        (
            "Review DPDP, sectoral standards, consent obligations, data transfers, and any "
            "industry-specific compliance commitments embedded in contracts."
        ),
        WorkstreamDomain.REGULATORY,
    ),
    _item(
        "regulatory.export_control_and_sanctions",
        "Screen export-control, sanctions, and cross-border restrictions",
        (
            "Check counterparties, geographies, products, and investors for sanctions exposure or "
            "cross-border restrictions relevant to closing and post-close operations."
        ),
        WorkstreamDomain.REGULATORY,
        mandatory=False,
    ),
    _item(
        "commercial.customer_concentration",
        "Assess customer concentration and retention quality",
        (
            "Measure top-customer dependence, renewal terms, cohort retention, churn, "
            "and upsell concentration."
        ),
        WorkstreamDomain.COMMERCIAL,
    ),
    _item(
        "commercial.pricing_and_discount_matrix",
        "Review pricing, discounting, and exception approvals",
        (
            "Assess list pricing, discount approval controls, renewal concessions, and whether "
            "reported ARR quality depends on exceptional pricing."
        ),
        WorkstreamDomain.COMMERCIAL,
    ),
    _item(
        "commercial.market_and_competitor_map",
        "Build market-position and competitor map",
        (
            "Summarize market sizing, win-loss dynamics, competitive threats, and differentiation "
            "claims that support the investment thesis."
        ),
        WorkstreamDomain.COMMERCIAL,
        mandatory=False,
    ),
    _item(
        "commercial.pipeline_quality_review",
        "Assess pipeline quality and conversion risk",
        (
            "Review pipeline aging, late-stage conversion, sales concentration, "
            "and back-end loaded "
            "bookings that could distort forecast reliability."
        ),
        WorkstreamDomain.COMMERCIAL,
    ),
    _item(
        "commercial.channel_partner_dependence",
        "Assess channel, distributor, or marketplace dependence",
        (
            "Measure revenue dependence on partners, resellers, or platforms and evaluate margin "
            "pressure from channel mix changes."
        ),
        WorkstreamDomain.COMMERCIAL,
        mandatory=False,
    ),
    _item(
        "commercial.revenue_quality_story",
        "Document revenue-quality story for investment committee",
        (
            "Translate concentration, retention, pricing, and renewal findings into a clear "
            "investment-committee narrative for valuation and deal risk."
        ),
        WorkstreamDomain.COMMERCIAL,
    ),
    _item(
        "operations.delivery_model",
        "Validate delivery concentration and operational dependencies",
        (
            "Check key personnel dependence, implementation bottlenecks, and cloud or "
            "outsourcing dependencies."
        ),
        WorkstreamDomain.OPERATIONS,
    ),
    _item(
        "operations.pmi_readiness_plan",
        "Prepare Day 1 and 100-day PMI readiness plan",
        (
            "Identify Day 1 dependencies, Day 100 integration priorities, TSA needs, org changes, "
            "and operating-model risks relevant to post-close integration."
        ),
        WorkstreamDomain.OPERATIONS,
    ),
    _item(
        "operations.business_continuity_resilience",
        "Assess business continuity and resilience dependencies",
        (
            "Review BCP, DR, single points of failure, capacity bottlenecks, and service "
            "resilience under growth and incident scenarios."
        ),
        WorkstreamDomain.OPERATIONS,
    ),
    _item(
        "operations.procurement_and_vendor_dependencies",
        "Review procurement and vendor dependency structure",
        (
            "Assess critical vendors, implementation partners, cloud dependencies, and switching "
            "costs that could constrain post-close plans."
        ),
        WorkstreamDomain.OPERATIONS,
        mandatory=False,
    ),
    _item(
        "cyber.privacy_controls",
        "Assess data privacy and security controls",
        (
            "Review security policies, incidents, access controls, processor contracts, "
            "and DPDP preparedness."
        ),
        WorkstreamDomain.CYBER_PRIVACY,
    ),
    _item(
        "cyber_privacy.day1_access_review",
        "Prepare Day 1 privileged-access and secrets transition review",
        (
            "Assess admin-access concentration, secrets ownership, shared credentials, and the "
            "controls needed for Day 1 access governance after close."
        ),
        WorkstreamDomain.CYBER_PRIVACY,
    ),
    _item(
        "cyber_privacy.incident_and_backlog_review",
        "Review incident history and remediation backlog",
        (
            "Summarize prior incidents, open vulnerabilities, unresolved pen-test findings, and "
            "material cyber remediation items relevant to deal protections."
        ),
        WorkstreamDomain.CYBER_PRIVACY,
    ),
    _item(
        "cyber_privacy.third_party_access_map",
        "Map third-party data processors and access pathways",
        (
            "Identify major processors, data-sharing pathways, privileged vendors, and exit risk "
            "if contracts or access models change post-close."
        ),
        WorkstreamDomain.CYBER_PRIVACY,
        mandatory=False,
    ),
    _item(
        "hr.key_talent_map",
        "Map key talent, founders, and retention dependencies",
        (
            "Identify mission-critical employees, founders, and revenue-linked operators whose "
            "retention is important to the investment case."
        ),
        WorkstreamDomain.HR,
        mandatory=False,
    ),
    _item(
        "hr.esop_and_incentive_review",
        "Review ESOP pool, grants, and incentive overhang",
        (
            "Assess vested and unvested grants, acceleration terms, dilution, and any change-in-"
            "control or retention pool implications."
        ),
        WorkstreamDomain.HR,
        mandatory=False,
    ),
    _item(
        "hr.labour_compliance_screen",
        "Assess labour-compliance posture",
        (
            "Review PF, ESI, Shops and Establishments, sexual-harassment committees, and employee "
            "grievance issues that could affect integration or reputational risk."
        ),
        WorkstreamDomain.HR,
        mandatory=False,
    ),
    _item(
        "forensic.related_party",
        "Map related-party flows and promoter-linked transactions",
        (
            "Trace intercompany balances, promoter entities, related-party sales or "
            "expenses, and any unusual round-tripping indicators."
        ),
        WorkstreamDomain.FORENSIC_COMPLIANCE,
    ),
    _item(
        "forensic.bank_flow_reconciliation",
        "Perform bank-flow and cash-leakage review",
        (
            "Review bank movements, unusual round sums, promoter withdrawals, and mismatches "
            "between statutory books and operating cash movement."
        ),
        WorkstreamDomain.FORENSIC_COMPLIANCE,
    ),
    _item(
        "forensic.whistleblower_and_fraud_history",
        "Review whistleblower, fraud, and misconduct history",
        (
            "Check prior investigations, whistleblower claims, internal-audit escalations, and "
            "disciplinary actions for governance or control concerns."
        ),
        WorkstreamDomain.FORENSIC_COMPLIANCE,
        mandatory=False,
    ),
    _item(
        "forensic.anti_bribery_and_third_party_controls",
        "Assess anti-bribery and third-party compliance controls",
        (
            "Review conflict-of-interest registers, anti-bribery policies, due diligence on high-"
            "risk intermediaries, and approval controls around gifts or facilitation risk."
        ),
        WorkstreamDomain.FORENSIC_COMPLIANCE,
    ),
    _item(
        "forensic.revenue_integrity_review",
        "Assess revenue-integrity anomalies and side-letter risk",
        (
            "Check side letters, channel stuffing, bill-and-hold arrangements, and unusual "
            "recognition patterns that could distort normalized performance."
        ),
        WorkstreamDomain.FORENSIC_COMPLIANCE,
    ),
)
CREDIT_LENDING_TEMPLATE: tuple[ChecklistTemplateItem, ...] = (
    _item(
        "financial_qoe.borrower_statements",
        "Collect borrower financial statements and monthly MIS",
        (
            "Validate the last three to five years of financial statements, monthly MIS, "
            "budget versus actuals, and management adjustments used for underwriting."
        ),
        WorkstreamDomain.FINANCIAL_QOE,
    ),
    _item(
        "financial_qoe.debt_service_capacity",
        "Assess debt-service capacity and cash flow resilience",
        (
            "Compute EBITDA to debt-service coverage, free cash flow, repayment "
            "seasonality, and downside capacity under stress scenarios."
        ),
        WorkstreamDomain.FINANCIAL_QOE,
    ),
    _item(
        "financial_qoe.working_capital_behaviour",
        "Review working-capital behaviour and collections quality",
        (
            "Analyse receivables aging, inventory turns where relevant, creditor stretch, "
            "cash conversion, and concentration in collections."
        ),
        WorkstreamDomain.FINANCIAL_QOE,
    ),
    _item(
        "financial_qoe.borrower_scorecard",
        "Prepare borrower scorecard and credit narrative",
        (
            "Summarize repayment capacity, liquidity resilience, leverage, collection quality, "
            "and management behavior into a reusable borrower scorecard."
        ),
        WorkstreamDomain.FINANCIAL_QOE,
    ),
    _item(
        "financial_qoe.base_case_underwriting",
        "Build base-case underwriting model",
        (
            "Construct the lender base case with key assumptions for revenue, margin, capex, "
            "working capital, and debt-service headroom."
        ),
        WorkstreamDomain.FINANCIAL_QOE,
    ),
    _item(
        "financial_qoe.downside_stress_case",
        "Build downside stress cases",
        (
            "Model downside cases for revenue compression, margin pressure, collections slippage, "
            "and covenant headroom deterioration."
        ),
        WorkstreamDomain.FINANCIAL_QOE,
    ),
    _item(
        "financial_qoe.collections_and_dpd_vintage",
        "Review collections behaviour and DPD vintage",
        (
            "Analyze receivables collections, overdue buckets, DPD migration, write-offs, and "
            "dispute-driven payment delays that could impair repayment."
        ),
        WorkstreamDomain.FINANCIAL_QOE,
    ),
    _item(
        "financial_qoe.borrowing_base_support",
        "Prepare borrowing-base support",
        (
            "Test the eligibility and haircuts of receivables, inventory, or other assets used to "
            "support a borrowing base."
        ),
        WorkstreamDomain.FINANCIAL_QOE,
        mandatory=False,
    ),
    _item(
        "financial_qoe.cash_sweep_and_waterfall",
        "Review cash sweep and repayment waterfall",
        (
            "Map contractual cash sweep, reserve requirements, restricted cash, and waterfall "
            "features relevant to lender control."
        ),
        WorkstreamDomain.FINANCIAL_QOE,
        mandatory=False,
    ),
    _item(
        "financial_qoe.management_adjustment_governance",
        "Review management adjustments used for underwriting",
        (
            "Assess whether non-recurring adjustments, run-rate claims, or promoter normalization "
            "assumptions are well supported before they influence sanctioned exposure."
        ),
        WorkstreamDomain.FINANCIAL_QOE,
    ),
    _item(
        "financial_qoe.promoter_support_dependence",
        "Assess promoter-support dependence",
        (
            "Check whether repayment assumptions rely on unsecured promoter support, shareholder "
            "funding, or non-binding support undertakings."
        ),
        WorkstreamDomain.FINANCIAL_QOE,
        mandatory=False,
    ),
    _item(
        "financial_qoe.liquidity_buffer_review",
        "Assess liquidity buffers and cash-management controls",
        (
            "Review minimum liquidity, treasury practices, cash pooling, and buffers needed to "
            "survive seasonal or downside collection stress."
        ),
        WorkstreamDomain.FINANCIAL_QOE,
    ),
    _item(
        "legal_corporate.security_package",
        "Validate security package and collateral perfection",
        (
            "Review charge filings, collateral coverage, guarantee structure, perfection "
            "steps, pari-passu exposures, and enforcement dependencies."
        ),
        WorkstreamDomain.LEGAL_CORPORATE,
    ),
    _item(
        "legal_corporate.collateral_cover_matrix",
        "Prepare collateral cover and recovery matrix",
        (
            "Map collateral classes, lenders, ranking, haircuts, insurance support, and estimated "
            "recovery considerations for the proposed facility."
        ),
        WorkstreamDomain.LEGAL_CORPORATE,
    ),
    _item(
        "legal_corporate.charge_perfection_check",
        "Check charge filings and perfection dependencies",
        (
            "Validate ROC charge status, filing gaps, perfection timing, and any third-party "
            "consents needed to complete the security package."
        ),
        WorkstreamDomain.LEGAL_CORPORATE,
    ),
    _item(
        "legal_corporate.guarantee_and_support_review",
        "Review guarantees, undertakings, and support structure",
        (
            "Assess guarantee enforceability, downstream support, negative pledges, and structural "
            "subordination risk across borrower and group entities."
        ),
        WorkstreamDomain.LEGAL_CORPORATE,
    ),
    _item(
        "legal_corporate.intercreditor_and_pari_passu_review",
        "Review intercreditor and pari-passu arrangements",
        (
            "Check existing lender agreements, ranking, standstill provisions, sharing mechanics, "
            "and consent requirements relevant to the new facility."
        ),
        WorkstreamDomain.LEGAL_CORPORATE,
        mandatory=False,
    ),
    _item(
        "legal_corporate.enforcement_dependency_review",
        "Assess enforcement dependencies and realizability",
        (
            "Document litigation dependencies, possession issues, title gaps, and enforcement "
            "frictions that could impair lender recovery."
        ),
        WorkstreamDomain.LEGAL_CORPORATE,
    ),
    _item(
        "legal_corporate.insurance_and_asset_protection",
        "Review insurance and asset-protection support",
        (
            "Assess whether collateral and operating assets are adequately "
            "insured and whether loss "
            "payee provisions support the contemplated lender structure."
        ),
        WorkstreamDomain.LEGAL_CORPORATE,
        mandatory=False,
    ),
    _item(
        "legal_corporate.board_and_borrowing_authorities",
        "Confirm borrowing authorities and corporate approvals",
        (
            "Validate board approvals, constitutional documents, shareholder "
            "consents, and sectoral "
            "permissions required for the proposed financing."
        ),
        WorkstreamDomain.LEGAL_CORPORATE,
    ),
    _item(
        "tax.compliance_borrower_status",
        "Confirm tax and statutory compliance status",
        (
            "Check GST, TDS, income-tax, PF, ESI, and other statutory compliance for "
            "signals that could impair repayment or create lender exposure."
        ),
        WorkstreamDomain.TAX,
    ),
    _item(
        "tax.tax_cash_leakage_review",
        "Assess tax-driven cash leakage",
        (
            "Quantify recurring tax leakage, disputed liabilities, and statutory arrears that "
            "could weaken DSCR or covenant headroom."
        ),
        WorkstreamDomain.TAX,
    ),
    _item(
        "tax.borrower_notice_and_demand_log",
        "Assemble borrower tax notice and demand log",
        (
            "Collect open notices, demands, appeals, and settlement plans for all major tax and "
            "statutory matters."
        ),
        WorkstreamDomain.TAX,
    ),
    _item(
        "tax.withholding_and_labour_arrears",
        "Review withholding and labour arrears",
        (
            "Check payroll, PF, ESI, and withholding arrears for signals of financial stress or "
            "control weakness affecting underwriting comfort."
        ),
        WorkstreamDomain.TAX,
    ),
    _item(
        "tax.indirect_tax_concentration",
        "Review indirect-tax concentration and pass-through risk",
        (
            "Assess dependence on rate assumptions, pass-through arrangements, and state-level "
            "filing quality that could affect cash realization."
        ),
        WorkstreamDomain.TAX,
        mandatory=False,
    ),
    _item(
        "regulatory.licensing_and_borrowing_constraints",
        "Review licensing, borrowing restrictions, and regulatory triggers",
        (
            "Check whether the borrower faces sectoral restrictions, consent "
            "requirements, FEMA implications, or regulatory approvals tied to financing."
        ),
        WorkstreamDomain.REGULATORY,
    ),
    _item(
        "regulatory.covenant_tracking_pack",
        "Build covenant tracking and early-warning pack",
        (
            "Document financial covenants, information covenants, testing dates, cure rights, "
            "waiver status, and early-warning triggers for ongoing monitoring."
        ),
        WorkstreamDomain.REGULATORY,
    ),
    _item(
        "regulatory.end_use_and_monitoring_controls",
        "Review end-use and monitoring controls",
        (
            "Check drawdown conditions, permitted end-use language, monitoring controls, auditor "
            "certification needs, and post-disbursement reporting obligations."
        ),
        WorkstreamDomain.REGULATORY,
    ),
    _item(
        "regulatory.related_party_financing_screen",
        "Screen related-party and group-financing constraints",
        (
            "Assess intercompany lending, related-party guarantees, upstreaming constraints, and "
            "regulatory restrictions that affect enforceability or priority."
        ),
        WorkstreamDomain.REGULATORY,
        mandatory=False,
    ),
    _item(
        "regulatory.customer_and_data_consents",
        "Review customer and data-consent constraints for cash collections",
        (
            "Check whether payments, mandates, or customer data flows rely on permissions or "
            "regulatory constructs that could impact collections continuity."
        ),
        WorkstreamDomain.REGULATORY,
        mandatory=False,
    ),
    _item(
        "commercial.counterparty_concentration",
        "Assess counterparty concentration and renewal dependence",
        (
            "Measure customer, dealer, distributor, or platform concentration that could "
            "impair collections and repayment continuity."
        ),
        WorkstreamDomain.COMMERCIAL,
    ),
    _item(
        "commercial.order_book_and_pipeline_quality",
        "Review order book and pipeline quality",
        (
            "Assess whether pipeline conversion, renewals, and customer concentration create "
            "volatility in collections or covenant headroom."
        ),
        WorkstreamDomain.COMMERCIAL,
        mandatory=False,
    ),
    _item(
        "commercial.price_pass_through_and_margin_risk",
        "Assess price pass-through and margin compression risk",
        (
            "Check whether the borrower can pass through cost changes and whether customer terms "
            "create sustained margin pressure affecting repayment."
        ),
        WorkstreamDomain.COMMERCIAL,
        mandatory=False,
    ),
    _item(
        "commercial.customer_payment_behaviour",
        "Review customer payment behaviour and concentration in collections",
        (
            "Analyze collections timing, disputes, deductions, and customer-level concentration in "
            "cash realization."
        ),
        WorkstreamDomain.COMMERCIAL,
    ),
    _item(
        "operations.inventory_and_asset_monitoring",
        "Review monitoring over inventory and financed assets",
        (
            "Assess stock reporting, asset tracking, inspection rights, and operational controls "
            "over financed assets or working-capital collateral."
        ),
        WorkstreamDomain.OPERATIONS,
        mandatory=False,
    ),
    _item(
        "operations.business_continuity_for_repayment",
        "Assess operational continuity for repayment capacity",
        (
            "Review single points of failure, key-man dependence, plant uptime, or service "
            "interruptions that could impair borrower cash generation."
        ),
        WorkstreamDomain.OPERATIONS,
    ),
    _item(
        "operations.management_reporting_pack",
        "Assess management reporting and lender MIS readiness",
        (
            "Validate whether borrower reporting can support covenant tracking, lender packs, and "
            "exception monitoring after sanction."
        ),
        WorkstreamDomain.OPERATIONS,
    ),
    _item(
        "operations.collections_escalation_model",
        "Review collections escalation and recovery governance",
        (
            "Check collections policies, recovery ownership, exception approvals, and escalation "
            "timelines for stressed accounts."
        ),
        WorkstreamDomain.OPERATIONS,
    ),
    _item(
        "cyber_privacy.payment_and_account_controls",
        "Review cyber controls around payments and banking access",
        (
            "Assess privileged access, maker-checker controls, banking access governance, and "
            "incident history relevant to fund control."
        ),
        WorkstreamDomain.CYBER_PRIVACY,
        mandatory=False,
    ),
    _item(
        "cyber_privacy.data_integrity_for_collections",
        "Assess data integrity for borrower collections data",
        (
            "Review system controls over receivables, collection dashboards, and MIS data used in "
            "underwriting and monitoring."
        ),
        WorkstreamDomain.CYBER_PRIVACY,
        mandatory=False,
    ),
    _item(
        "cyber_privacy.threat_and_incident_review",
        "Review threat and incident backlog",
        (
            "Check whether unresolved cyber incidents or control gaps could impair operating "
            "resilience, payment integrity, or lender monitoring confidence."
        ),
        WorkstreamDomain.CYBER_PRIVACY,
        mandatory=False,
    ),
    _item(
        "forensic.end_use_and_fund_flow",
        "Test end-use of funds and diversion risk",
        (
            "Review bank statements, related-party flows, unusual round-tripping, "
            "promoter withdrawals, and deviations from stated end-use."
        ),
        WorkstreamDomain.FORENSIC_COMPLIANCE,
    ),
    _item(
        "forensic.bank_statement_variance_review",
        "Perform bank-statement variance review",
        (
            "Reconcile sanctioned end-use, bank outflows, related-party transfers, and high-risk "
            "cash movements to identify diversion or stress signals."
        ),
        WorkstreamDomain.FORENSIC_COMPLIANCE,
    ),
    _item(
        "forensic.borrower_integrity_review",
        "Review promoter and borrower integrity signals",
        (
            "Screen for undisclosed related parties, litigation, fraud allegations, and history of "
            "misreporting or covenant evasion."
        ),
        WorkstreamDomain.FORENSIC_COMPLIANCE,
    ),
    _item(
        "forensic.fraud_and_evergreening_signals",
        "Assess fraud, evergreening, and window-dressing signals",
        (
            "Check quarter-end inflows, rollover behavior, related-party settlements, and invoice "
            "patterns that may disguise repayment stress."
        ),
        WorkstreamDomain.FORENSIC_COMPLIANCE,
    ),
    _item(
        "forensic.connected_party_exposure",
        "Assess connected-party exposure in repayment flows",
        (
            "Quantify group-company dependence, promoter support, and borrower concentration in "
            "connected parties that could distort true risk."
        ),
        WorkstreamDomain.FORENSIC_COMPLIANCE,
    ),
    _item(
        "hr.management_depth_and_succession",
        "Assess management depth and succession",
        (
            "Review dependence on founder or promoter decision-making for collections, treasury, "
            "and operational continuity."
        ),
        WorkstreamDomain.HR,
        mandatory=False,
    ),
    _item(
        "hr.control_owner_matrix",
        "Map control owners across finance and operations",
        (
            "Identify whether key financial controls, collections processes, or reporting duties "
            "are concentrated in a small set of individuals."
        ),
        WorkstreamDomain.HR,
        mandatory=False,
    ),
)
VENDOR_ONBOARDING_TEMPLATE: tuple[ChecklistTemplateItem, ...] = (
    _item(
        "legal_corporate.vendor_registration",
        "Validate vendor registration, ownership, and contracting authority",
        (
            "Confirm incorporation details, beneficial ownership, contracting authority, "
            "and whether any material corporate changes are pending."
        ),
        WorkstreamDomain.LEGAL_CORPORATE,
    ),
    _item(
        "legal_corporate.contractual_risk",
        "Review contracting model, liability caps, and subcontracting rights",
        (
            "Check standard terms, limitation of liability, indemnities, confidentiality, "
            "termination rights, and subcontracting permissions."
        ),
        WorkstreamDomain.LEGAL_CORPORATE,
    ),
    _item(
        "legal_corporate.vendor_msa_playbook",
        "Prepare vendor-MSA negotiation playbook",
        (
            "Document liability, indemnity, audit rights, security addenda, SLA credits, and "
            "termination terms needed before onboarding."
        ),
        WorkstreamDomain.LEGAL_CORPORATE,
    ),
    _item(
        "legal_corporate.data_processing_addendum",
        "Review data-processing and confidentiality addenda",
        (
            "Check DPA, cross-border transfer language, subprocessors, breach notifications, and "
            "data-return obligations required by the onboarding workflow."
        ),
        WorkstreamDomain.LEGAL_CORPORATE,
    ),
    _item(
        "legal_corporate.ip_and_deliverable_rights",
        "Review IP, work-product, and deliverable rights",
        (
            "Check ownership, licensing, open-source obligations, and exit rights over vendor-"
            "created work product or managed services."
        ),
        WorkstreamDomain.LEGAL_CORPORATE,
    ),
    _item(
        "legal_corporate.subcontractor_and_flowdown_rights",
        "Assess subcontractor rights and flow-down controls",
        (
            "Review subcontracting permissions, critical subprocessor dependencies, and the extent "
            "to which contractual obligations flow down to lower-tier vendors."
        ),
        WorkstreamDomain.LEGAL_CORPORATE,
    ),
    _item(
        "legal_corporate.exit_assistance_rights",
        "Review exit assistance and transition obligations",
        (
            "Assess whether the vendor must support transition-out, data return, "
            "knowledge transfer, "
            "and operational continuity if the relationship is terminated."
        ),
        WorkstreamDomain.LEGAL_CORPORATE,
        mandatory=False,
    ),
    _item(
        "legal_corporate.insurance_certificate_pack",
        "Collect insurance certificates and limits summary",
        (
            "Validate cyber, professional indemnity, general liability, worker compensation, and "
            "other coverage required by the onboarding policy."
        ),
        WorkstreamDomain.LEGAL_CORPORATE,
        mandatory=False,
    ),
    _item(
        "legal_corporate.contracting_entity_perimeter",
        "Map contracting-entity perimeter and affiliates",
        (
            "Identify the exact legal entity, parent, affiliates, delivery centers, and cross-"
            "border group entities involved in service delivery."
        ),
        WorkstreamDomain.LEGAL_CORPORATE,
    ),
    _item(
        "legal_corporate.signatory_and_board_authority",
        "Confirm signatory and board authority",
        (
            "Verify signatory powers, board approvals, and internal delegations used by the vendor "
            "to execute binding contracts."
        ),
        WorkstreamDomain.LEGAL_CORPORATE,
    ),
    _item(
        "tax.vendor_statutory_profile",
        "Confirm GST, PAN, and statutory compliance standing",
        (
            "Validate GST registration, return filing posture, withholding-tax readiness, "
            "and whether open statutory defaults could impair onboarding."
        ),
        WorkstreamDomain.TAX,
    ),
    _item(
        "tax.invoice_and_withholding_readiness",
        "Review invoicing and withholding readiness",
        (
            "Validate invoice structure, GST invoicing, withholding treatment, and reverse-charge "
            "considerations that affect onboarding operations."
        ),
        WorkstreamDomain.TAX,
    ),
    _item(
        "tax.vendor_notice_and_default_log",
        "Assemble vendor notice and default log",
        (
            "Collect tax notices, labour defaults, and statutory non-compliance that may affect "
            "vendor approval or trigger enhanced oversight."
        ),
        WorkstreamDomain.TAX,
    ),
    _item(
        "tax.pe_and_cross_border_screen",
        "Screen permanent-establishment and cross-border tax risk",
        (
            "Assess PE, withholding, and cross-border tax posture for offshore delivery models or "
            "intercompany service structures."
        ),
        WorkstreamDomain.TAX,
        mandatory=False,
    ),
    _item(
        "tax.contract_tax_gross_up_terms",
        "Review gross-up and tax-indemnity contract terms",
        (
            "Check whether proposed vendor terms create gross-up, withholding disputes, or tax-"
            "indemnity exposures for the onboarding entity."
        ),
        WorkstreamDomain.TAX,
        mandatory=False,
    ),
    _item(
        "regulatory.vendor_restrictions",
        "Screen regulatory restrictions, sanctions, and licensing triggers",
        (
            "Check whether the vendor or its principals face sanctions, licensing gaps, "
            "watchlist alerts, or sector-specific onboarding restrictions."
        ),
        WorkstreamDomain.REGULATORY,
    ),
    _item(
        "regulatory.vendor_risk_tier",
        "Assign vendor risk tier and review cadence",
        (
            "Classify the vendor into a risk tier based on service criticality, data access, "
            "regulatory exposure, and integrity findings."
        ),
        WorkstreamDomain.REGULATORY,
    ),
    _item(
        "regulatory.license_and_sectoral_perimeter",
        "Review licences and sectoral operating perimeter",
        (
            "Validate that the vendor has the licences, registrations, and permissions needed to "
            "perform the contracted services in the relevant jurisdictions."
        ),
        WorkstreamDomain.REGULATORY,
    ),
    _item(
        "regulatory.sanctions_and_watchlist_screen",
        "Perform sanctions, watchlist, and adverse-media screen",
        (
            "Screen the entity, beneficial owners, and key principals against sanctions, PEP, "
            "watchlist, and adverse-media sources before onboarding."
        ),
        WorkstreamDomain.REGULATORY,
    ),
    _item(
        "regulatory.data_residency_and_transfer_screen",
        "Assess data residency and transfer restrictions",
        (
            "Review data localization, transfer restrictions, and sectoral "
            "privacy obligations that "
            "affect where the vendor can store or process enterprise data."
        ),
        WorkstreamDomain.REGULATORY,
    ),
    _item(
        "regulatory.subprocessor_notification_obligations",
        "Review subprocessor notification and approval obligations",
        (
            "Check notification rights, approval workflows, and contractual obligations when the "
            "vendor changes subprocessors or delivery locations."
        ),
        WorkstreamDomain.REGULATORY,
        mandatory=False,
    ),
    _item(
        "cyber_privacy.vendor_security_posture",
        "Assess cyber, privacy, and access-control posture",
        (
            "Review security controls, data-handling obligations, incident history, "
            "sub-processor use, and privacy commitments relevant to onboarding."
        ),
        WorkstreamDomain.CYBER_PRIVACY,
    ),
    _item(
        "cyber_privacy.vendor_questionnaire",
        "Review vendor security and privacy questionnaire",
        (
            "Assess questionnaire completion, control evidence, remediation responses, and any "
            "material unanswered questions required for onboarding approval."
        ),
        WorkstreamDomain.CYBER_PRIVACY,
    ),
    _item(
        "cyber_privacy.vendor_certifications",
        "Validate vendor certifications and attestations",
        (
            "Collect ISO, SOC, PCI, business-continuity, and privacy attestations required by the "
            "vendor-risk framework."
        ),
        WorkstreamDomain.CYBER_PRIVACY,
    ),
    _item(
        "cyber_privacy.privileged_access_matrix",
        "Review privileged-access and remote-access matrix",
        (
            "Identify admin access, VPN pathways, shared credentials, and privileged tooling that "
            "the vendor would use in the proposed operating model."
        ),
        WorkstreamDomain.CYBER_PRIVACY,
    ),
    _item(
        "cyber_privacy.incident_response_and_notification",
        "Assess incident response and notification obligations",
        (
            "Validate incident-handling procedures, breach-notification timing, "
            "and escalation paths "
            "required for third-party risk approval."
        ),
        WorkstreamDomain.CYBER_PRIVACY,
    ),
    _item(
        "cyber_privacy.data_retention_and_deletion",
        "Review data retention, deletion, and return controls",
        (
            "Check retention schedules, deletion certification, and data return obligations across "
            "systems, backups, and subcontractors."
        ),
        WorkstreamDomain.CYBER_PRIVACY,
    ),
    _item(
        "cyber_privacy.application_and_network_segmentation",
        "Assess application and network segmentation controls",
        (
            "Evaluate tenant isolation, environment segregation, and network controls relevant to "
            "the vendor's service model and data sensitivity."
        ),
        WorkstreamDomain.CYBER_PRIVACY,
        mandatory=False,
    ),
    _item(
        "cyber_privacy.identity_and_joiner_mover_leaver_controls",
        "Review identity lifecycle and JML controls",
        (
            "Validate access provisioning, revocation, maker-checker controls, and background "
            "checks for vendor staff with enterprise access."
        ),
        WorkstreamDomain.CYBER_PRIVACY,
    ),
    _item(
        "cyber_privacy.business_continuity_testing",
        "Review business continuity and disaster-recovery testing",
        (
            "Assess DR coverage, recovery objectives, recent test outcomes, and any gaps for the "
            "services being onboarded."
        ),
        WorkstreamDomain.CYBER_PRIVACY,
    ),
    _item(
        "forensic.third_party_integrity",
        "Review third-party integrity and anti-bribery risk",
        (
            "Check integrity red flags, beneficial-owner concerns, conflicts of interest, "
            "anti-bribery controls, and whistleblower or misconduct signals."
        ),
        WorkstreamDomain.FORENSIC_COMPLIANCE,
    ),
    _item(
        "forensic.beneficial_owner_transparency",
        "Review beneficial-owner transparency and conflicts",
        (
            "Identify opaque ownership structures, politically exposed persons, "
            "employee conflicts, "
            "and undisclosed group-company relationships."
        ),
        WorkstreamDomain.FORENSIC_COMPLIANCE,
    ),
    _item(
        "forensic.commission_and_channel_integrity",
        "Assess commission, referral, and channel integrity",
        (
            "Review referral fees, commission structures, gifts, and sales-agent dependence for "
            "anti-bribery or procurement-integrity concerns."
        ),
        WorkstreamDomain.FORENSIC_COMPLIANCE,
        mandatory=False,
    ),
    _item(
        "forensic.invoice_fraud_and_duplicate_payment_screen",
        "Screen for invoice fraud and duplicate payment risk",
        (
            "Assess invoice controls, bank-account ownership, and duplicate-payment risks relevant "
            "to procurement and onboarding controls."
        ),
        WorkstreamDomain.FORENSIC_COMPLIANCE,
        mandatory=False,
    ),
    _item(
        "forensic.subprocessor_integrity_screen",
        "Assess integrity screening over subprocessors",
        (
            "Review whether critical subcontractors and delivery partners have been screened and "
            "whether their controls materially affect third-party risk."
        ),
        WorkstreamDomain.FORENSIC_COMPLIANCE,
        mandatory=False,
    ),
    _item(
        "operations.service_continuity",
        "Test operational resilience and dependency concentration",
        (
            "Review delivery resilience, key-person dependence, single-location exposure, "
            "and any concentration that could disrupt service continuity."
        ),
        WorkstreamDomain.OPERATIONS,
    ),
    _item(
        "operations.sla_and_support_model",
        "Review SLA, escalation, and support model",
        (
            "Assess service windows, escalation coverage, support staffing, and "
            "unresolved delivery "
            "risks in the proposed operating model."
        ),
        WorkstreamDomain.OPERATIONS,
    ),
    _item(
        "operations.subprocessor_and_delivery_map",
        "Map subprocessors, delivery locations, and service dependencies",
        (
            "Document who delivers the service, where it is delivered from, and which critical "
            "subcontractors or facilities underpin continuity."
        ),
        WorkstreamDomain.OPERATIONS,
    ),
    _item(
        "operations.bcp_failover_and_capacity",
        "Assess failover, capacity, and operational surge readiness",
        (
            "Review whether the vendor can absorb growth, shift locations, and continue servicing "
            "the account during outages or staff attrition."
        ),
        WorkstreamDomain.OPERATIONS,
    ),
    _item(
        "operations.exit_transition_dependencies",
        "Assess exit-transition and reversibility dependencies",
        (
            "Review dependencies that would make the vendor difficult to replace, including data "
            "format lock-in, knowledge concentration, and shared tools."
        ),
        WorkstreamDomain.OPERATIONS,
        mandatory=False,
    ),
    _item(
        "commercial.vendor_criticality_assessment",
        "Assess vendor business criticality",
        (
            "Determine whether the vendor supports revenue, regulated "
            "operations, customer data, or "
            "mission-critical internal workflows that warrant enhanced diligence."
        ),
        WorkstreamDomain.COMMERCIAL,
    ),
    _item(
        "commercial.pricing_and_renewal_terms",
        "Review pricing, renewal, and lock-in terms",
        (
            "Assess termination fees, renewal mechanics, pricing escalators, and lock-in features "
            "that affect long-term third-party risk."
        ),
        WorkstreamDomain.COMMERCIAL,
        mandatory=False,
    ),
    _item(
        "commercial.single_vendor_dependency",
        "Assess single-vendor dependency risk",
        (
            "Review whether the enterprise relies on the vendor for a unique capability, critical "
            "workflow, or hard-to-replace knowledge domain."
        ),
        WorkstreamDomain.COMMERCIAL,
    ),
    _item(
        "financial_qoe.vendor_financial_resilience",
        "Review vendor financial resilience",
        (
            "Assess basic solvency, cash runway, leverage, and adverse financial indicators that "
            "could impair service continuity."
        ),
        WorkstreamDomain.FINANCIAL_QOE,
        mandatory=False,
    ),
    _item(
        "financial_qoe.payment_dependency_and_prepayment_risk",
        "Assess payment dependency and prepayment risk",
        (
            "Review prepayment structures, volume commitments, and working-capital dependence that "
            "could create supplier or cash-flow stress."
        ),
        WorkstreamDomain.FINANCIAL_QOE,
        mandatory=False,
    ),
    _item(
        "financial_qoe.financial_monitoring_triggers",
        "Define financial monitoring triggers for ongoing review",
        (
            "Set triggers such as overdue filings, distress signals, concentration changes, and "
            "cash-flow deterioration for periodic vendor review."
        ),
        WorkstreamDomain.FINANCIAL_QOE,
        mandatory=False,
    ),
    _item(
        "hr.background_screening_and_access_training",
        "Review background screening and access training",
        (
            "Assess pre-employment screening, confidentiality training, and "
            "role-based awareness for "
            "vendor staff with access to enterprise systems or data."
        ),
        WorkstreamDomain.HR,
        mandatory=False,
    ),
    _item(
        "hr.key_person_dependency_map",
        "Map key-person and founder dependency",
        (
            "Identify whether delivery quality or escalation handling depends on "
            "founders or a small "
            "group of named employees."
        ),
        WorkstreamDomain.HR,
        mandatory=False,
    ),
    _item(
        "hr.workforce_turnover_and_coverage",
        "Review workforce turnover and shift coverage",
        (
            "Assess attrition, backup staffing, and whether the vendor can "
            "maintain coverage during "
            "leave, attrition, or rapid demand changes."
        ),
        WorkstreamDomain.HR,
        mandatory=False,
    ),
    _item(
        "hr.insider_risk_and_conflict_reporting",
        "Assess insider-risk and conflict reporting mechanisms",
        (
            "Review conflict declarations, disciplinary controls, and insider-risk reporting over "
            "staff who handle sensitive data or privileged access."
        ),
        WorkstreamDomain.HR,
        mandatory=False,
    ),
)


TECH_SAAS_TEMPLATE: tuple[ChecklistTemplateItem, ...] = (
    _item(
        "commercial.customer_concentration",
        "Assess customer concentration and retention quality",
        (
            "Measure top-customer dependence, renewal terms, cohort retention, churn, "
            "and upsell concentration."
        ),
        WorkstreamDomain.COMMERCIAL,
    ),
    _item(
        "cyber.privacy_controls",
        "Assess data privacy and security controls",
        (
            "Review security policies, incidents, access controls, processor contracts, "
            "and DPDP preparedness."
        ),
        WorkstreamDomain.CYBER_PRIVACY,
    ),
    _item(
        "operations.delivery_model",
        "Validate delivery concentration and operational dependencies",
        (
            "Check key personnel dependence, implementation bottlenecks, and cloud or "
            "outsourcing dependencies."
        ),
        WorkstreamDomain.OPERATIONS,
    ),
)


MANUFACTURING_INDUSTRIALS_TEMPLATE: tuple[ChecklistTemplateItem, ...] = (
    _item(
        "financial_qoe.inventory_quality",
        "Assess inventory quality, aging, and scrap exposure",
        (
            "Review raw material, WIP, and finished-goods aging, obsolete stock, "
            "scrap write-offs, and standard-cost versus actual-margin leakage."
        ),
        WorkstreamDomain.FINANCIAL_QOE,
    ),
    _item(
        "operations.plant_capacity_utilisation",
        "Validate plant capacity, utilisation, and maintenance resilience",
        (
            "Review plant capacity, OEE or utilisation, unplanned downtime, "
            "maintenance backlog, and dependence on a single site or line."
        ),
        WorkstreamDomain.OPERATIONS,
    ),
    _item(
        "operations.supplier_concentration",
        "Assess supplier concentration and raw-material continuity",
        (
            "Measure single-source supplier dependence, raw-material volatility, "
            "import dependencies, and continuity planning for key inputs."
        ),
        WorkstreamDomain.OPERATIONS,
    ),
    _item(
        "regulatory.ehs_factory_compliance",
        "Review factory, environmental, and EHS compliance",
        (
            "Validate factory licences, consent-to-operate status, hazardous-waste "
            "controls, pollution control obligations, and major accident history."
        ),
        WorkstreamDomain.REGULATORY,
    ),
    _item(
        "commercial.orderbook_channel_mix",
        "Review order book, dealer mix, and channel concentration",
        (
            "Assess order-book quality, customer and dealer concentration, export "
            "dependence, cancellation trends, and pricing pass-through ability."
        ),
        WorkstreamDomain.COMMERCIAL,
    ),
    _item(
        "forensic.procurement_related_party",
        "Trace procurement leakages and related-party vendor exposure",
        (
            "Check related-party procurement, unusual vendor pricing, round-tripped "
            "purchases, and capex flows linked to promoter entities."
        ),
        WorkstreamDomain.FORENSIC_COMPLIANCE,
    ),
)


BFSI_NBFC_TEMPLATE: tuple[ChecklistTemplateItem, ...] = (
    _item(
        "financial_qoe.asset_quality_and_provisioning",
        "Review asset quality, stage migration, and provisioning adequacy",
        (
            "Assess GNPA or NNPA trends, stage migration, write-offs, restructures, "
            "and provisioning adequacy across key borrower cohorts and products."
        ),
        WorkstreamDomain.FINANCIAL_QOE,
    ),
    _item(
        "financial_qoe.alm_liquidity_profile",
        "Assess ALM, liquidity buffers, and borrowing concentration",
        (
            "Review maturity mismatches, liquidity buffers, funding concentration, "
            "asset-liability gaps, and refinancing dependence under stress."
        ),
        WorkstreamDomain.FINANCIAL_QOE,
    ),
    _item(
        "regulatory.rbi_registration_and_returns",
        "Validate RBI registration, product perimeter, and regulatory returns",
        (
            "Confirm registration status, product or licence perimeter, supervisory "
            "history, and completeness of required RBI or statutory returns."
        ),
        WorkstreamDomain.REGULATORY,
    ),
    _item(
        "operations.underwriting_and_collections_governance",
        "Review underwriting exceptions and collections governance",
        (
            "Assess policy exceptions, scorecard overrides, collections conduct, "
            "outsourced collections oversight, and grievance escalation controls."
        ),
        WorkstreamDomain.OPERATIONS,
    ),
    _item(
        "cyber_privacy.kyc_aml_and_data_controls",
        "Assess KYC, AML-monitoring, and customer-data controls",
        (
            "Review onboarding controls, CKYC or KYC hygiene, AML monitoring, "
            "customer consent handling, and privileged access over borrower data."
        ),
        WorkstreamDomain.CYBER_PRIVACY,
    ),
    _item(
        "forensic.connected_lending_and_evergreening",
        "Test connected lending, evergreening, and unusual fund flows",
        (
            "Trace connected lending, loan evergreening indicators, related-party "
            "exposure, rollovers, and round-tripped fund movements."
        ),
        WorkstreamDomain.FORENSIC_COMPLIANCE,
    ),
)


def build_motion_pack_template(motion_pack: MotionPack) -> tuple[ChecklistTemplateItem, ...]:
    if motion_pack == MotionPack.BUY_SIDE_DILIGENCE:
        return BUY_SIDE_TEMPLATE
    if motion_pack == MotionPack.CREDIT_LENDING:
        return CREDIT_LENDING_TEMPLATE
    if motion_pack == MotionPack.VENDOR_ONBOARDING:
        return VENDOR_ONBOARDING_TEMPLATE
    return ()


def build_sector_pack_template(sector_pack: SectorPack) -> tuple[ChecklistTemplateItem, ...]:
    if sector_pack == SectorPack.TECH_SAAS_SERVICES:
        return TECH_SAAS_TEMPLATE
    if sector_pack == SectorPack.MANUFACTURING_INDUSTRIALS:
        return MANUFACTURING_INDUSTRIALS_TEMPLATE
    if sector_pack == SectorPack.BFSI_NBFC:
        return BFSI_NBFC_TEMPLATE
    return ()
