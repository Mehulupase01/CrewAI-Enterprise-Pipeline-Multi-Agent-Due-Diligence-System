const API_BASE_URL = (
  process.env.API_BASE_URL ??
  process.env.NEXT_PUBLIC_API_BASE_URL ??
  "http://127.0.0.1:8000/api/v1"
).replace(/\/$/, "");

export type PlatformOverview = {
  product_name: string;
  current_phase: string;
  country: string;
  motion_packs: string[];
  sector_packs: string[];
  workstream_domains: string[];
  severity_scale: string[];
};

export type CaseSummary = {
  id: string;
  name: string;
  target_name: string;
  country: string;
  summary: string | null;
  motion_pack: string;
  sector_pack: string;
  status: string;
  created_at: string;
  updated_at: string;
};

export type DocumentArtifactSummary = {
  id: string;
  title: string;
  original_filename: string | null;
  source_kind: string;
  document_kind: string;
  mime_type: string | null;
  processing_status: string;
  storage_path: string | null;
  parser_name: string | null;
  sha256_digest: string | null;
  byte_size: number | null;
  created_at: string;
  updated_at: string;
};

export type EvidenceItemSummary = {
  id: string;
  title: string;
  evidence_kind: string;
  workstream_domain: string;
  citation: string;
  excerpt: string;
  artifact_id: string | null;
  confidence: number;
  created_at: string;
  updated_at: string;
};

export type RequestItemSummary = {
  id: string;
  title: string;
  detail: string;
  owner: string | null;
  status: string;
  created_at: string;
  updated_at: string;
};

export type QaItemSummary = {
  id: string;
  question: string;
  requested_by: string | null;
  response: string | null;
  status: string;
  created_at: string;
  updated_at: string;
};

export type IssueRegisterItemSummary = {
  id: string;
  title: string;
  summary: string;
  severity: string;
  status: string;
  workstream_domain: string;
  business_impact: string;
  recommended_action: string | null;
  source_evidence_id: string | null;
  confidence: number;
  created_at: string;
  updated_at: string;
};

export type ChecklistItemSummary = {
  id: string;
  title: string;
  detail: string;
  workstream_domain: string;
  mandatory: boolean;
  evidence_required: boolean;
  owner: string | null;
  note: string | null;
  template_key: string | null;
  status: string;
  created_at: string;
  updated_at: string;
};

export type ApprovalDecisionSummary = {
  id: string;
  reviewer: string;
  note: string | null;
  decision: string;
  rationale: string;
  ready_for_export: boolean;
  open_mandatory_items: number;
  blocking_issue_count: number;
  created_at: string;
  updated_at: string;
};

export type RunTraceEventSummary = {
  id: string;
  run_id: string;
  sequence_number: number;
  step_key: string;
  title: string;
  message: string;
  level: string;
  created_at: string;
  updated_at: string;
};

export type ReportBundleSummary = {
  id: string;
  run_id: string;
  bundle_kind: string;
  title: string;
  format: string;
  summary: string | null;
  content: string;
  file_name?: string | null;
  storage_path?: string | null;
  sha256_digest?: string | null;
  byte_size?: number | null;
  created_at: string;
  updated_at: string;
};

export type RunExportPackageSummary = {
  id: string;
  case_id: string;
  run_id: string;
  export_kind: string;
  title: string;
  format: string;
  file_name: string;
  summary: string | null;
  requested_by: string;
  storage_path: string;
  sha256_digest: string;
  byte_size: number;
  included_files: string[];
  created_at: string;
  updated_at: string;
};

export type WorkstreamSynthesisSummary = {
  id: string;
  run_id: string;
  workstream_domain: string;
  status: string;
  headline: string;
  narrative: string;
  finding_count: number;
  blocker_count: number;
  confidence: number;
  recommended_next_action: string;
  created_at: string;
  updated_at: string;
};

export type WorkflowRunSummary = {
  id: string;
  case_id: string;
  requested_by: string;
  note: string | null;
  report_template: string;
  status: string;
  summary: string | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
  updated_at: string;
};

export type WorkflowRunDetail = WorkflowRunSummary & {
  trace_events: RunTraceEventSummary[];
  report_bundles: ReportBundleSummary[];
  export_packages: RunExportPackageSummary[];
  workstream_syntheses: WorkstreamSynthesisSummary[];
};

export type CaseDetail = CaseSummary & {
  documents: DocumentArtifactSummary[];
  evidence_items: EvidenceItemSummary[];
  request_items: RequestItemSummary[];
  qa_items: QaItemSummary[];
  issues: IssueRegisterItemSummary[];
  checklist_items: ChecklistItemSummary[];
  approvals: ApprovalDecisionSummary[];
};

export type DashboardData = {
  overview: PlatformOverview;
  cases: CaseSummary[];
  featuredCase: CaseDetail;
  latestRun: WorkflowRunDetail;
  isFallback: boolean;
};

type CaseWorkspaceData = {
  caseDetail: CaseDetail;
  runs: WorkflowRunSummary[];
  isFallback: boolean;
};

type RunWorkspaceData = {
  caseDetail: CaseDetail;
  run: WorkflowRunDetail;
  isFallback: boolean;
};

async function fetchJson<T>(path: string): Promise<T | null> {
  try {
    const response = await fetch(`${API_BASE_URL}${path}`, { cache: "no-store" });
    if (!response.ok) {
      return null;
    }
    return (await response.json()) as T;
  } catch {
    return null;
  }
}

const demoOverview: PlatformOverview = {
  product_name: "CrewAI Enterprise Pipeline",
  current_phase: "Phase 12 complete: Sector Pack Deepening",
  country: "India",
  motion_packs: ["buy_side_diligence", "credit_lending", "vendor_onboarding"],
  sector_packs: ["tech_saas_services", "manufacturing_industrials", "bfsi_nbfc"],
  workstream_domains: [
    "financial_qoe",
    "legal_corporate",
    "tax",
    "regulatory",
    "commercial",
    "cyber_privacy",
  ],
  severity_scale: ["critical", "high", "medium", "low", "info"],
};

const demoCase: CaseDetail = {
  id: "alpha-nimbus-acquisition",
  name: "Alpha Nimbus Acquisition",
  target_name: "Nimbus Data Systems",
  country: "India",
  summary: "Buy-side diligence for an India-based vertical SaaS target.",
  motion_pack: "buy_side_diligence",
  sector_pack: "tech_saas_services",
  status: "in_review",
  created_at: "2026-03-25T09:00:00Z",
  updated_at: "2026-03-26T11:30:00Z",
  documents: [
    {
      id: "doc-financials",
      title: "FY25 audited financials",
      original_filename: "fy25-audited-financials.pdf",
      source_kind: "uploaded_dataroom",
      document_kind: "audited_financials",
      mime_type: "application/pdf",
      processing_status: "parsed",
      storage_path: "file:///cases/alpha/fy25-audited-financials.pdf",
      parser_name: "pdfplumber",
      sha256_digest: "demo-sha256-financials",
      byte_size: 182443,
      created_at: "2026-03-25T09:10:00Z",
      updated_at: "2026-03-25T09:11:00Z",
    },
    {
      id: "doc-board",
      title: "Board minutes Q4 FY25",
      original_filename: "q4-board-minutes.docx",
      source_kind: "management_response",
      document_kind: "board_minutes",
      mime_type: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
      processing_status: "parsed",
      storage_path: "file:///cases/alpha/q4-board-minutes.docx",
      parser_name: "docx",
      sha256_digest: "demo-sha256-board",
      byte_size: 43322,
      created_at: "2026-03-25T09:14:00Z",
      updated_at: "2026-03-25T09:15:00Z",
    },
  ],
  evidence_items: [
    {
      id: "ev-deferred-revenue",
      title: "Deferred revenue reconciliation",
      evidence_kind: "metric",
      workstream_domain: "financial_qoe",
      citation: "FY25 audited financials, Note 12",
      excerpt: "Deferred revenue increased by 28 percent driven by annual contracts.",
      artifact_id: "doc-financials",
      confidence: 0.91,
      created_at: "2026-03-25T09:16:00Z",
      updated_at: "2026-03-25T09:16:00Z",
    },
    {
      id: "ev-gst-notice",
      title: "GST notice summary",
      evidence_kind: "risk",
      workstream_domain: "tax",
      citation: "CBIC notice pack FY25",
      excerpt: "The company received a GST notice seeking additional tax demand in two states.",
      artifact_id: null,
      confidence: 0.92,
      created_at: "2026-03-25T09:18:00Z",
      updated_at: "2026-03-25T09:18:00Z",
    },
    {
      id: "ev-customer-concentration",
      title: "Top-customer concentration",
      evidence_kind: "risk",
      workstream_domain: "commercial",
      citation: "Revenue cohort workbook, tab 4",
      excerpt: "One enterprise customer contributes 41 percent of ARR.",
      artifact_id: null,
      confidence: 0.84,
      created_at: "2026-03-25T09:20:00Z",
      updated_at: "2026-03-25T09:20:00Z",
    },
  ],
  request_items: [
    {
      id: "req-monthly-bridge",
      title: "Provide monthly churn bridge",
      detail: "Need monthly logo churn, NRR bridge, and annual contract roll-forward for the last 24 months.",
      owner: "Finance Controller",
      status: "open",
      created_at: "2026-03-25T09:22:00Z",
      updated_at: "2026-03-26T08:05:00Z",
    },
    {
      id: "req-gst",
      title: "Upload GST demand papers",
      detail: "Need all notices, replies, and challans for open GST matters.",
      owner: "Tax Controller",
      status: "open",
      created_at: "2026-03-25T09:23:00Z",
      updated_at: "2026-03-26T08:09:00Z",
    },
  ],
  qa_items: [
    {
      id: "qa-impl-revenue",
      question: "Why did implementation revenue spike in Q3 FY25?",
      requested_by: "Financial workstream",
      response: "Two large enterprise onboarding milestones were accepted in the same quarter.",
      status: "answered",
      created_at: "2026-03-25T09:24:00Z",
      updated_at: "2026-03-25T10:00:00Z",
    },
  ],
  issues: [
    {
      id: "issue-gst",
      title: "Outstanding tax or GST exposure",
      summary: "The target has unresolved GST demands across two operating states.",
      severity: "high",
      status: "open",
      workstream_domain: "tax",
      business_impact: "Could require escrow, indemnity, and a purchase price adjustment.",
      recommended_action: "Collect full notice history and quantify cash leakage.",
      source_evidence_id: "ev-gst-notice",
      confidence: 0.92,
      created_at: "2026-03-25T09:30:00Z",
      updated_at: "2026-03-25T09:30:00Z",
    },
    {
      id: "issue-deferred-revenue",
      title: "Unreconciled deferred revenue movement",
      summary: "Monthly movement does not reconcile cleanly to audited annual balances.",
      severity: "high",
      status: "in_review",
      workstream_domain: "financial_qoe",
      business_impact: "May affect normalized ARR quality and working-capital assumptions.",
      recommended_action: "Obtain a month-by-month revenue waterfall and sample contracts.",
      source_evidence_id: "ev-deferred-revenue",
      confidence: 0.86,
      created_at: "2026-03-25T09:31:00Z",
      updated_at: "2026-03-26T08:30:00Z",
    },
    {
      id: "issue-concentration",
      title: "Customer concentration exposure",
      summary: "One enterprise client contributes 41 percent of ARR.",
      severity: "medium",
      status: "open",
      workstream_domain: "commercial",
      business_impact: "Revenue downside is meaningful if renewal slips.",
      recommended_action: "Stress test the forecast and review renewal protections.",
      source_evidence_id: "ev-customer-concentration",
      confidence: 0.84,
      created_at: "2026-03-25T09:32:00Z",
      updated_at: "2026-03-25T09:32:00Z",
    },
  ],
  checklist_items: [
    {
      id: "check-financials",
      title: "Collect audited financial statements for the last five years",
      detail: "Validate annual statement coverage, auditor notes, and management adjustments.",
      workstream_domain: "financial_qoe",
      mandatory: true,
      evidence_required: true,
      owner: "Finance Lead",
      note: "FY21-FY25 set available.",
      template_key: "financial_qoe.audited_financials",
      status: "satisfied",
      created_at: "2026-03-25T09:05:00Z",
      updated_at: "2026-03-25T09:40:00Z",
    },
    {
      id: "check-monthly-bridge",
      title: "Obtain monthly revenue and margin bridge",
      detail: "Reconcile monthly revenue, margin, deferred revenue, and churn drivers.",
      workstream_domain: "financial_qoe",
      mandatory: true,
      evidence_required: true,
      owner: "Finance Controller",
      note: "Still waiting on contract cohort detail.",
      template_key: "financial_qoe.monthly_bridge",
      status: "in_progress",
      created_at: "2026-03-25T09:06:00Z",
      updated_at: "2026-03-26T08:00:00Z",
    },
    {
      id: "check-contracts",
      title: "Review material customer, vendor, and financing contracts",
      detail: "Check change-of-control, termination, assignment, and pricing protections.",
      workstream_domain: "legal_corporate",
      mandatory: true,
      evidence_required: true,
      owner: "Legal Lead",
      note: "Top ten customer contracts still under legal review.",
      template_key: "legal_corporate.material_contracts",
      status: "in_progress",
      created_at: "2026-03-25T09:07:00Z",
      updated_at: "2026-03-26T07:45:00Z",
    },
    {
      id: "check-gst",
      title: "Reconcile direct and indirect tax exposures",
      detail: "Collect GST, TDS, income-tax filings, notices, demands, and payments.",
      workstream_domain: "tax",
      mandatory: true,
      evidence_required: true,
      owner: "Tax Lead",
      note: "Open GST demands still unresolved.",
      template_key: "tax.notice_register",
      status: "blocked",
      created_at: "2026-03-25T09:08:00Z",
      updated_at: "2026-03-26T08:10:00Z",
    },
    {
      id: "check-customer-concentration",
      title: "Assess customer concentration and retention quality",
      detail: "Measure top-customer dependence, renewal terms, and churn sensitivity.",
      workstream_domain: "commercial",
      mandatory: true,
      evidence_required: true,
      owner: "Commercial Lead",
      note: "Need renewal deck from management.",
      template_key: "commercial.customer_concentration",
      status: "in_progress",
      created_at: "2026-03-25T09:09:00Z",
      updated_at: "2026-03-26T08:15:00Z",
    },
  ],
  approvals: [
    {
      id: "approval-ic-review",
      reviewer: "IC Reviewer",
      note: "Case blocked until GST exposure and monthly bridge are resolved.",
      decision: "changes_requested",
      rationale: "Case is not ready for export because mandatory items and high-severity tax issues remain open.",
      ready_for_export: false,
      open_mandatory_items: 4,
      blocking_issue_count: 2,
      created_at: "2026-03-26T09:00:00Z",
      updated_at: "2026-03-26T09:00:00Z",
    },
  ],
};

const demoRun: WorkflowRunDetail = {
  id: "run-20260326-001",
  case_id: demoCase.id,
  requested_by: "Diligence Operator",
  note: "Generate current state memo and issue pack.",
  report_template: "standard",
  status: "completed",
  summary: "Generated 3 report bundles and 4 workstream syntheses with visible blockers.",
  started_at: "2026-03-26T09:10:00Z",
  completed_at: "2026-03-26T09:11:00Z",
  created_at: "2026-03-26T09:10:00Z",
  updated_at: "2026-03-26T09:11:00Z",
  trace_events: [
    {
      id: "trace-1",
      run_id: "run-20260326-001",
      sequence_number: 1,
      step_key: "case_snapshot",
      title: "Case snapshot loaded",
      message: "Loaded 2 documents, 3 evidence items, and 2 request items.",
      level: "info",
      created_at: "2026-03-26T09:10:10Z",
      updated_at: "2026-03-26T09:10:10Z",
    },
    {
      id: "trace-2",
      run_id: "run-20260326-001",
      sequence_number: 2,
      step_key: "issue_triage",
      title: "Issue register reviewed",
      message: "Detected 3 active issues across the current case state.",
      level: "info",
      created_at: "2026-03-26T09:10:15Z",
      updated_at: "2026-03-26T09:10:15Z",
    },
    {
      id: "trace-3",
      run_id: "run-20260326-001",
      sequence_number: 3,
      step_key: "coverage_check",
      title: "Checklist coverage computed",
      message: "4 mandatory checklist items remain open.",
      level: "warning",
      created_at: "2026-03-26T09:10:20Z",
      updated_at: "2026-03-26T09:10:20Z",
    },
    {
      id: "trace-4",
      run_id: "run-20260326-001",
      sequence_number: 4,
      step_key: "approval_snapshot",
      title: "Approval state captured",
      message: "Latest decision: changes_requested",
      level: "info",
      created_at: "2026-03-26T09:10:25Z",
      updated_at: "2026-03-26T09:10:25Z",
    },
    {
      id: "trace-5",
      run_id: "run-20260326-001",
      sequence_number: 5,
      step_key: "workstream_synthesis",
      title: "Workstream syntheses generated",
      message: "Generated 4 workstream summaries for the current run.",
      level: "info",
      created_at: "2026-03-26T09:10:35Z",
      updated_at: "2026-03-26T09:10:35Z",
    },
    {
      id: "trace-6",
      run_id: "run-20260326-001",
      sequence_number: 6,
      step_key: "report_bundle_generation",
      title: "Report bundles generated",
      message: "Executive memo, issue register, and workstream synthesis bundles were rendered.",
      level: "info",
      created_at: "2026-03-26T09:10:40Z",
      updated_at: "2026-03-26T09:10:40Z",
    },
  ],
  report_bundles: [
    {
      id: "bundle-memo",
      run_id: "run-20260326-001",
      bundle_kind: "executive_memo_markdown",
      title: "Executive Memo",
      format: "markdown",
      summary: "Investor-style memo generated from the current case state.",
      content: [
        "# Executive Memo: Alpha Nimbus Acquisition",
        "",
        "## Summary",
        "The case remains blocked by tax exposure, customer concentration follow-up, and incomplete financial QoE bridges.",
      ].join("\n"),
      created_at: "2026-03-26T09:10:45Z",
      updated_at: "2026-03-26T09:10:45Z",
    },
    {
      id: "bundle-issues",
      run_id: "run-20260326-001",
      bundle_kind: "issue_register_markdown",
      title: "Issue Register",
      format: "markdown",
      summary: "Sorted issue register snapshot generated from the current case.",
      content: [
        "# Issue Register",
        "",
        "- [high] Outstanding tax or GST exposure",
        "- [high] Unreconciled deferred revenue movement",
        "- [medium] Customer concentration exposure",
      ].join("\n"),
      created_at: "2026-03-26T09:10:46Z",
      updated_at: "2026-03-26T09:10:46Z",
    },
    {
      id: "bundle-synthesis",
      run_id: "run-20260326-001",
      bundle_kind: "workstream_synthesis_markdown",
      title: "Workstream Syntheses",
      format: "markdown",
      summary: "Run-level synthesis by diligence workstream.",
      content: [
        "# Workstream Syntheses",
        "",
        "## Financial Qoe",
        "Status: needs_follow_up",
        "",
        "## Tax",
        "Status: blocked",
      ].join("\n"),
      created_at: "2026-03-26T09:10:47Z",
      updated_at: "2026-03-26T09:10:47Z",
    },
  ],
  export_packages: [
    {
      id: "export-1",
      case_id: "alpha-nimbus-acquisition",
      run_id: "run-20260326-001",
      export_kind: "run_report_archive",
      title: "Board Pack Export",
      format: "zip",
      file_name: "alpha-nimbus-acquisition-run-20260326-001-export.zip",
      summary: "Archive package for workflow run run-20260326-001 with 7 generated files.",
      requested_by: "Diligence Operator",
      storage_path: "file:///cases/alpha/exports/alpha-nimbus-acquisition-run-20260326-001-export.zip",
      sha256_digest: "demo-export-sha256",
      byte_size: 18432,
      included_files: [
        "README.txt",
        "manifest.json",
        "reports/executive_memo.md",
        "reports/issue_register.md",
        "reports/workstream_syntheses.md",
        "data/run_trace.json",
        "data/case_snapshot.json",
      ],
      created_at: "2026-03-26T09:11:00Z",
      updated_at: "2026-03-26T09:11:00Z",
    },
  ],
  workstream_syntheses: [
    {
      id: "syn-financial",
      run_id: "run-20260326-001",
      workstream_domain: "financial_qoe",
      status: "needs_follow_up",
      headline: "Financial Qoe needs follow-up before sign-off.",
      narrative: "Financial QoE synthesis: the evidence ledger includes one item and one active issue. One mandatory checklist item still needs completion.",
      finding_count: 2,
      blocker_count: 1,
      confidence: 0.8,
      recommended_next_action: "Obtain a month-by-month revenue waterfall and sample contracts.",
      created_at: "2026-03-26T09:10:30Z",
      updated_at: "2026-03-26T09:10:30Z",
    },
    {
      id: "syn-legal",
      run_id: "run-20260326-001",
      workstream_domain: "legal_corporate",
      status: "needs_follow_up",
      headline: "Legal Corporate needs follow-up before sign-off.",
      narrative: "Legal Corporate synthesis: no direct evidence has been logged yet and no active issue-register entries in this lane. One mandatory checklist item still needs completion.",
      finding_count: 0,
      blocker_count: 1,
      confidence: 0.55,
      recommended_next_action: "Check change-of-control, termination, assignment, and pricing protections.",
      created_at: "2026-03-26T09:10:31Z",
      updated_at: "2026-03-26T09:10:31Z",
    },
    {
      id: "syn-tax",
      run_id: "run-20260326-001",
      workstream_domain: "tax",
      status: "blocked",
      headline: "Tax is blocked by 2 unresolved items.",
      narrative: "Tax synthesis: the evidence ledger includes one item with one active issue under this workstream. One mandatory checklist item still needs completion. Highest-priority concern: Outstanding tax or GST exposure.",
      finding_count: 2,
      blocker_count: 2,
      confidence: 0.85,
      recommended_next_action: "Collect full notice history and quantify cash leakage.",
      created_at: "2026-03-26T09:10:32Z",
      updated_at: "2026-03-26T09:10:32Z",
    },
    {
      id: "syn-commercial",
      run_id: "run-20260326-001",
      workstream_domain: "commercial",
      status: "needs_follow_up",
      headline: "Commercial needs follow-up before sign-off.",
      narrative: "Commercial synthesis: the evidence ledger includes one item with one active issue under this workstream. One mandatory checklist item still needs completion.",
      finding_count: 2,
      blocker_count: 1,
      confidence: 0.8,
      recommended_next_action: "Stress test the forecast and review renewal protections.",
      created_at: "2026-03-26T09:10:33Z",
      updated_at: "2026-03-26T09:10:33Z",
    },
  ],
};

function formatStatusLabel(value: string) {
  return value
    .replace(/_/g, " ")
    .replace(/\b\w/g, (character) => character.toUpperCase());
}

async function getRealDashboardData(): Promise<DashboardData | null> {
  const [overview, cases] = await Promise.all([
    fetchJson<PlatformOverview>("/system/overview"),
    fetchJson<CaseSummary[]>("/cases"),
  ]);

  if (overview === null || cases === null || cases.length === 0) {
    return null;
  }

  const featuredCase = await fetchJson<CaseDetail>(`/cases/${cases[0].id}`);
  if (featuredCase === null) {
    return null;
  }

  const runs = await fetchJson<WorkflowRunSummary[]>(`/cases/${featuredCase.id}/runs`);
  const latestRun =
    runs && runs.length > 0
      ? await fetchJson<WorkflowRunDetail>(
          `/cases/${featuredCase.id}/runs/${runs[0].id}`,
        )
      : null;

  if (latestRun === null) {
    return null;
  }

  return {
    overview,
    cases,
    featuredCase,
    latestRun,
    isFallback: false,
  };
}

export async function getDashboardData(): Promise<DashboardData> {
  const realData = await getRealDashboardData();
  if (realData !== null) {
    return realData;
  }

  return {
    overview: demoOverview,
    cases: [demoCase],
    featuredCase: demoCase,
    latestRun: demoRun,
    isFallback: true,
  };
}

export async function getCaseWorkspace(caseId: string): Promise<CaseWorkspaceData | null> {
  const caseDetail = await fetchJson<CaseDetail>(`/cases/${caseId}`);
  if (caseDetail !== null) {
    const runs = (await fetchJson<WorkflowRunSummary[]>(`/cases/${caseId}/runs`)) ?? [];
    return { caseDetail, runs, isFallback: false };
  }

  if (caseId === demoCase.id) {
    return {
      caseDetail: demoCase,
      runs: [demoRun],
      isFallback: true,
    };
  }

  return null;
}

export async function getRunWorkspace(
  caseId: string,
  runId: string,
): Promise<RunWorkspaceData | null> {
  const caseDetail = await fetchJson<CaseDetail>(`/cases/${caseId}`);
  const run = await fetchJson<WorkflowRunDetail>(`/cases/${caseId}/runs/${runId}`);
  if (caseDetail !== null && run !== null) {
    return { caseDetail, run, isFallback: false };
  }

  if (caseId === demoCase.id && runId === demoRun.id) {
    return {
      caseDetail: demoCase,
      run: demoRun,
      isFallback: true,
    };
  }

  return null;
}

export function summarizeCase(caseDetail: CaseDetail) {
  return {
    issueCount: caseDetail.issues.length,
    blockingIssueCount: caseDetail.issues.filter((issue) =>
      ["critical", "high"].includes(issue.severity),
    ).length,
    documentCount: caseDetail.documents.length,
    evidenceCount: caseDetail.evidence_items.length,
    openRequestCount: caseDetail.request_items.filter(
      (request) => request.status !== "closed",
    ).length,
    approvalState:
      caseDetail.approvals.length > 0
        ? formatStatusLabel(caseDetail.approvals[caseDetail.approvals.length - 1].decision)
        : "No Review Yet",
  };
}

export function summarizeRun(run: WorkflowRunDetail) {
  return {
    traceCount: run.trace_events.length,
    bundleCount: run.report_bundles.length,
    exportCount: run.export_packages.length,
    synthesisCount: run.workstream_syntheses.length,
  };
}

export function labelize(value: string) {
  return formatStatusLabel(value);
}
