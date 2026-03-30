"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { updateQaItem, updateRequest } from "@/lib/api-client";
import type {
  QaItemSummary,
  RequestItemSummary,
} from "@/lib/workbench-data";

import styles from "./interactive.module.css";

const REQUEST_STATUSES = ["open", "in_progress", "closed"];
const QA_STATUSES = ["open", "answered", "closed"];

function labelize(value: string) {
  return value
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

export default function RequestQaPanel({
  caseId,
  requests,
  qaItems,
}: {
  caseId: string;
  requests: RequestItemSummary[];
  qaItems: QaItemSummary[];
}) {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);

  async function handleRequestStatusChange(
    requestId: string,
    newStatus: string,
  ) {
    setError(null);
    try {
      await updateRequest(caseId, requestId, { status: newStatus });
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Update failed");
    }
  }

  async function handleQaStatusChange(qaId: string, newStatus: string) {
    setError(null);
    try {
      await updateQaItem(caseId, qaId, { status: newStatus });
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Update failed");
    }
  }

  return (
    <div>
      {error && <p className={styles.errorMsg}>{error}</p>}

      <h3 style={{ fontSize: "1.06rem", marginBottom: 12 }}>
        Diligence Requests
      </h3>
      {requests.length === 0 ? (
        <p style={{ color: "var(--muted)", padding: "12px 0" }}>
          No open requests.
        </p>
      ) : (
        requests.map((req) => (
          <div key={req.id} style={{ padding: "10px 0" }}>
            <div style={{ marginBottom: 6 }}>
              <strong>{req.title}</strong>
              <p style={{ color: "var(--muted)", fontSize: "0.88rem" }}>
                {req.detail}
              </p>
              <p style={{ color: "var(--muted)", fontSize: "0.82rem" }}>
                Owner: {req.owner ?? "Unassigned"}
              </p>
            </div>
            <div className={styles.inlineEdit}>
              <select
                className={styles.inlineSelect}
                value={req.status}
                onChange={(e) =>
                  handleRequestStatusChange(req.id, e.target.value)
                }
              >
                {REQUEST_STATUSES.map((s) => (
                  <option key={s} value={s}>
                    {labelize(s)}
                  </option>
                ))}
              </select>
            </div>
          </div>
        ))
      )}

      <h3 style={{ fontSize: "1.06rem", margin: "18px 0 12px" }}>
        Q&amp;A Items
      </h3>
      {qaItems.length === 0 ? (
        <p style={{ color: "var(--muted)", padding: "12px 0" }}>
          No Q&amp;A items captured.
        </p>
      ) : (
        qaItems.map((qa) => (
          <div key={qa.id} style={{ padding: "10px 0" }}>
            <div style={{ marginBottom: 6 }}>
              <strong>{qa.question}</strong>
              <p style={{ color: "var(--muted)", fontSize: "0.88rem" }}>
                {qa.response ?? "Awaiting response."}
              </p>
              <p style={{ color: "var(--muted)", fontSize: "0.82rem" }}>
                Requested by: {qa.requested_by ?? "Unknown"}
              </p>
            </div>
            <div className={styles.inlineEdit}>
              <select
                className={styles.inlineSelect}
                value={qa.status}
                onChange={(e) =>
                  handleQaStatusChange(qa.id, e.target.value)
                }
              >
                {QA_STATUSES.map((s) => (
                  <option key={s} value={s}>
                    {labelize(s)}
                  </option>
                ))}
              </select>
            </div>
          </div>
        ))
      )}
    </div>
  );
}
