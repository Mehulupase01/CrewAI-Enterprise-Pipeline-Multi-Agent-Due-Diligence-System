"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { reviewCase } from "@/lib/api-client";
import type { ApprovalDecisionSummary } from "@/lib/workbench-data";

import styles from "./interactive.module.css";

const DECISIONS = [
  "approved",
  "changes_requested",
  "conditionally_approved",
  "rejected",
];

function labelize(value: string) {
  return value
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

export default function ApprovalPanel({
  caseId,
  approvals,
}: {
  caseId: string;
  approvals: ApprovalDecisionSummary[];
}) {
  const router = useRouter();
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [reviewer, setReviewer] = useState("");
  const [note, setNote] = useState("");
  const [decision, setDecision] = useState("");

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!reviewer.trim()) return;
    setPending(true);
    setError(null);
    try {
      await reviewCase(caseId, {
        reviewer: reviewer.trim(),
        note: note.trim() || undefined,
        decision: decision || undefined,
      });
      setReviewer("");
      setNote("");
      setDecision("");
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Review failed");
    } finally {
      setPending(false);
    }
  }

  const latestApproval = approvals.length > 0
    ? approvals[approvals.length - 1]
    : null;

  return (
    <div>
      {latestApproval && (
        <div
          style={{
            padding: "14px 18px",
            borderRadius: 18,
            background: "rgba(20, 36, 51, 0.04)",
            marginBottom: 16,
          }}
        >
          <p style={{ fontSize: "0.82rem", color: "var(--muted)" }}>
            Latest review by <strong>{latestApproval.reviewer}</strong>
          </p>
          <p>
            <strong>{labelize(latestApproval.decision)}</strong>
          </p>
          <p style={{ color: "var(--muted)", fontSize: "0.88rem" }}>
            {latestApproval.rationale}
          </p>
          <p style={{ fontSize: "0.82rem", color: "var(--muted)" }}>
            Ready for export: {latestApproval.ready_for_export ? "Yes" : "No"} |
            Open mandatory: {latestApproval.open_mandatory_items} |
            Blocking issues: {latestApproval.blocking_issue_count}
          </p>
        </div>
      )}

      <form onSubmit={handleSubmit}>
        <div className={styles.fieldGroup}>
          <div className={styles.field}>
            <label className={styles.fieldLabel}>Reviewer Name</label>
            <input
              className={styles.input}
              type="text"
              value={reviewer}
              onChange={(e) => setReviewer(e.target.value)}
              placeholder="e.g. IC Reviewer"
              required
            />
          </div>

          <div className={styles.field}>
            <label className={styles.fieldLabel}>
              Decision Override (optional)
            </label>
            <select
              className={styles.select}
              value={decision}
              onChange={(e) => setDecision(e.target.value)}
            >
              <option value="">Auto-compute from case state</option>
              {DECISIONS.map((d) => (
                <option key={d} value={d}>
                  {labelize(d)}
                </option>
              ))}
            </select>
          </div>

          <div className={styles.field}>
            <label className={styles.fieldLabel}>Note (optional)</label>
            <textarea
              className={styles.textarea}
              value={note}
              onChange={(e) => setNote(e.target.value)}
              placeholder="Reviewer notes..."
            />
          </div>
        </div>

        {error && <p className={styles.errorMsg}>{error}</p>}

        <div className={styles.btnRow}>
          <button
            type="submit"
            className={styles.btnPrimary}
            disabled={pending || !reviewer.trim()}
          >
            {pending ? "Submitting..." : "Submit Review"}
          </button>
        </div>
      </form>
    </div>
  );
}
