"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import {
  deleteIssue,
  scanIssues,
  updateIssue,
} from "@/lib/api-client";
import type { IssueRegisterItemSummary } from "@/lib/workbench-data";

import styles from "./interactive.module.css";

const ISSUE_STATUSES = ["open", "in_review", "mitigated", "accepted", "closed"];
const SEVERITIES = ["critical", "high", "medium", "low", "info"];

function labelize(value: string) {
  return value
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

export default function IssueManager({
  caseId,
  issues,
}: {
  caseId: string;
  issues: IssueRegisterItemSummary[];
}) {
  const router = useRouter();
  const [scanning, setScanning] = useState(false);
  const [scanResult, setScanResult] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleScan() {
    setScanning(true);
    setError(null);
    setScanResult(null);
    try {
      const result = await scanIssues(caseId);
      setScanResult(`Scan complete: ${result.issues_created} new issues flagged`);
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Scan failed");
    } finally {
      setScanning(false);
    }
  }

  async function handleStatusChange(issueId: string, newStatus: string) {
    try {
      await updateIssue(caseId, issueId, { status: newStatus });
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Update failed");
    }
  }

  async function handleSeverityChange(issueId: string, newSeverity: string) {
    try {
      await updateIssue(caseId, issueId, { severity: newSeverity });
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Update failed");
    }
  }

  async function handleDelete(issueId: string) {
    try {
      await deleteIssue(caseId, issueId);
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Delete failed");
    }
  }

  return (
    <div>
      <div className={styles.actionBar}>
        <button
          className={styles.btnPrimary}
          onClick={handleScan}
          disabled={scanning}
        >
          {scanning ? "Scanning..." : "Scan Issues"}
        </button>
        {scanResult && <span className={styles.successMsg}>{scanResult}</span>}
      </div>

      {error && <p className={styles.errorMsg}>{error}</p>}

      {issues.length === 0 ? (
        <p style={{ color: "var(--muted)", padding: "18px" }}>
          No issues registered yet. Upload documents and run a scan.
        </p>
      ) : (
        issues.map((issue) => (
          <div key={issue.id} style={{ padding: "10px 0" }}>
            <div style={{ marginBottom: 6 }}>
              <strong>{issue.title}</strong>
              <p style={{ color: "var(--muted)", fontSize: "0.88rem" }}>
                {issue.business_impact}
              </p>
            </div>
            <div className={styles.inlineEdit}>
              <select
                className={styles.inlineSelect}
                value={issue.status}
                onChange={(e) => handleStatusChange(issue.id, e.target.value)}
              >
                {ISSUE_STATUSES.map((s) => (
                  <option key={s} value={s}>
                    {labelize(s)}
                  </option>
                ))}
              </select>
              <select
                className={styles.inlineSelect}
                value={issue.severity}
                onChange={(e) => handleSeverityChange(issue.id, e.target.value)}
              >
                {SEVERITIES.map((s) => (
                  <option key={s} value={s}>
                    {labelize(s)}
                  </option>
                ))}
              </select>
              <button
                className={`${styles.btnDanger} ${styles.btnSmall}`}
                onClick={() => handleDelete(issue.id)}
              >
                Remove
              </button>
            </div>
          </div>
        ))
      )}
    </div>
  );
}
