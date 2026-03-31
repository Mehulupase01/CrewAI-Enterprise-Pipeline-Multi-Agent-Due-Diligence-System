"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { createExportPackage, createRun } from "@/lib/api-client";

import styles from "./interactive.module.css";

type ReportTemplate = "standard" | "lender" | "board_memo" | "one_pager";

export default function RunWorkflowButton({ caseId }: { caseId: string }) {
  const router = useRouter();
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [note, setNote] = useState("");
  const [reportTemplate, setReportTemplate] = useState<ReportTemplate>("standard");

  async function handleRun(e: React.FormEvent) {
    e.preventDefault();
    setPending(true);
    setError(null);
    try {
      const result = await createRun(caseId, {
        requested_by: "Workbench Analyst",
        note: note.trim() || undefined,
        report_template: reportTemplate,
      });
      if ("trace_events" in result) {
        try {
          await createExportPackage(caseId, result.id, {
            title: `${reportTemplate.replaceAll("_", " ")} export package`,
          });
        } catch {
          // Export generation is helpful but should not block a successful run.
        }
        router.push(`/cases/${caseId}/runs/${result.id}`);
      }
      setShowForm(false);
      setNote("");
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Run failed");
    } finally {
      setPending(false);
    }
  }

  if (!showForm) {
    return (
      <button className={styles.btnPrimary} onClick={() => setShowForm(true)}>
        Run Workflow
      </button>
    );
  }

  return (
    <form onSubmit={handleRun} style={{ display: "grid", gap: 10 }}>
      <div className={styles.field}>
        <label className={styles.fieldLabel}>Operator Note (optional)</label>
        <input
          className={styles.input}
          type="text"
          value={note}
          onChange={(e) => setNote(e.target.value)}
          placeholder="e.g. Generate current state memo"
        />
      </div>
      <div className={styles.field}>
        <label className={styles.fieldLabel}>Report Template</label>
        <select
          className={styles.select}
          value={reportTemplate}
          onChange={(e) => setReportTemplate(e.target.value as ReportTemplate)}
        >
          <option value="standard">Standard</option>
          <option value="lender">Lender</option>
          <option value="board_memo">Board memo</option>
          <option value="one_pager">One-pager</option>
        </select>
      </div>
      {error && <p className={styles.errorMsg}>{error}</p>}
      <div className={styles.btnRow}>
        <button
          type="button"
          className={styles.btnSecondary}
          onClick={() => setShowForm(false)}
          disabled={pending}
        >
          Cancel
        </button>
        <button type="submit" className={styles.btnPrimary} disabled={pending}>
          {pending ? "Running..." : "Execute Run"}
        </button>
      </div>
    </form>
  );
}
