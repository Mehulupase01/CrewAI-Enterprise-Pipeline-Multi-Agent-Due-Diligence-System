/**
 * Typed API client for POST/PATCH/DELETE mutations against the FastAPI backend.
 * All calls are routed through the Next.js rewrite proxy (/api/v1/...).
 */

import type {
  ApprovalDecisionSummary,
  CaseDetail,
  CaseSummary,
  ChecklistItemSummary,
  IssueRegisterItemSummary,
  QaItemSummary,
  RequestItemSummary,
  WorkflowRunDetail,
  WorkflowRunSummary,
} from "./workbench-data";

const DEFAULT_HEADERS: Record<string, string> = {
  "X-CEP-User-Id": "analyst-1",
  "X-CEP-User-Name": "Workbench Analyst",
  "X-CEP-User-Email": "analyst@crew.ai",
  "X-CEP-User-Role": "ANALYST",
};

type MutationOptions = {
  role?: "ANALYST" | "REVIEWER" | "ADMIN";
};

function authHeaders(opts?: MutationOptions): Record<string, string> {
  const headers = { ...DEFAULT_HEADERS };
  if (opts?.role) {
    headers["X-CEP-User-Role"] = opts.role;
  }
  return headers;
}

async function mutateJson<T>(
  path: string,
  method: "POST" | "PATCH" | "DELETE",
  body?: unknown,
  opts?: MutationOptions,
): Promise<T> {
  const headers: Record<string, string> = {
    ...authHeaders(opts),
  };
  if (body !== undefined) {
    headers["Content-Type"] = "application/json";
  }
  const res = await fetch(`/api/v1${path}`, {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`${method} ${path} failed (${res.status}): ${text}`);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

async function mutateFormData<T>(
  path: string,
  formData: FormData,
  opts?: MutationOptions,
): Promise<T> {
  const res = await fetch(`/api/v1${path}`, {
    method: "POST",
    headers: authHeaders(opts),
    body: formData,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`POST ${path} failed (${res.status}): ${text}`);
  }
  return res.json() as Promise<T>;
}

// ── Cases ───────────────────────────────────────────────────────────

export type CaseCreatePayload = {
  name: string;
  target_name: string;
  motion_pack: string;
  sector_pack: string;
  country?: string;
  summary?: string;
};

export async function createCase(data: CaseCreatePayload): Promise<CaseSummary> {
  return mutateJson("/cases", "POST", data);
}

export type CaseUpdatePayload = {
  name?: string;
  target_name?: string;
  summary?: string;
  status?: string;
};

export async function updateCase(caseId: string, data: CaseUpdatePayload): Promise<CaseDetail> {
  return mutateJson(`/cases/${caseId}`, "PATCH", data);
}

export async function deleteCase(caseId: string): Promise<void> {
  return mutateJson(`/cases/${caseId}`, "DELETE");
}

// ── Documents ───────────────────────────────────────────────────────

export type DocumentIngestionResult = {
  artifact_id: string;
  evidence_created: number;
  chunks_created: number;
  entities_extracted: number;
};

export async function uploadDocument(
  caseId: string,
  file: File,
  documentKind: string,
  sourceKind: string,
  workstreamDomain: string,
): Promise<DocumentIngestionResult> {
  const form = new FormData();
  form.append("file", file);
  form.append("document_kind", documentKind);
  form.append("source_kind", sourceKind);
  form.append("workstream_domain", workstreamDomain);
  return mutateFormData(`/cases/${caseId}/documents/upload`, form);
}

export async function deleteDocument(caseId: string, docId: string): Promise<void> {
  return mutateJson(`/cases/${caseId}/documents/${docId}`, "DELETE");
}

// ── Checklist ───────────────────────────────────────────────────────

export type ChecklistSeedResult = { seeded: number };

export async function seedChecklist(caseId: string): Promise<ChecklistSeedResult> {
  return mutateJson(`/cases/${caseId}/checklist/seed`, "POST");
}

// ── Issues ──────────────────────────────────────────────────────────

export type IssueScanResult = { issues_created: number };

export async function scanIssues(caseId: string): Promise<IssueScanResult> {
  return mutateJson(`/cases/${caseId}/issues/scan`, "POST");
}

export type IssueUpdatePayload = {
  status?: string;
  severity?: string;
  recommended_action?: string;
};

export async function updateIssue(
  caseId: string,
  issueId: string,
  data: IssueUpdatePayload,
): Promise<IssueRegisterItemSummary> {
  return mutateJson(`/cases/${caseId}/issues/${issueId}`, "PATCH", data);
}

export async function deleteIssue(caseId: string, issueId: string): Promise<void> {
  return mutateJson(`/cases/${caseId}/issues/${issueId}`, "DELETE");
}

// ── Checklist items ─────────────────────────────────────────────────

export type ChecklistUpdatePayload = {
  status?: string;
  note?: string;
  owner?: string;
};

export async function updateChecklistItem(
  caseId: string,
  itemId: string,
  data: ChecklistUpdatePayload,
): Promise<ChecklistItemSummary> {
  return mutateJson(`/cases/${caseId}/checklist/${itemId}`, "PATCH", data);
}

// ── Requests ────────────────────────────────────────────────────────

export type RequestUpdatePayload = {
  status?: string;
  owner?: string;
};

export async function updateRequest(
  caseId: string,
  requestId: string,
  data: RequestUpdatePayload,
): Promise<RequestItemSummary> {
  return mutateJson(`/cases/${caseId}/requests/${requestId}`, "PATCH", data);
}

// ── Q&A ─────────────────────────────────────────────────────────────

export type QaUpdatePayload = {
  response?: string;
  status?: string;
};

export async function updateQaItem(
  caseId: string,
  qaId: string,
  data: QaUpdatePayload,
): Promise<QaItemSummary> {
  return mutateJson(`/cases/${caseId}/qa/${qaId}`, "PATCH", data);
}

// ── Approvals ───────────────────────────────────────────────────────

export type ApprovalReviewPayload = {
  reviewer: string;
  note?: string;
  decision?: string;
};

export async function reviewCase(
  caseId: string,
  data: ApprovalReviewPayload,
): Promise<ApprovalDecisionSummary> {
  return mutateJson(`/cases/${caseId}/approvals/review`, "POST", data, { role: "REVIEWER" });
}

// ── Workflow Runs ───────────────────────────────────────────────────

export type RunCreatePayload = {
  requested_by: string;
  note?: string;
};

export async function createRun(
  caseId: string,
  data: RunCreatePayload,
): Promise<WorkflowRunDetail | WorkflowRunSummary> {
  return mutateJson(`/cases/${caseId}/runs`, "POST", data);
}

// ── Export Packages ─────────────────────────────────────────────────

export async function createExportPackage(
  caseId: string,
  runId: string,
): Promise<{ id: string }> {
  return mutateJson(`/cases/${caseId}/runs/${runId}/export-package`, "POST");
}
