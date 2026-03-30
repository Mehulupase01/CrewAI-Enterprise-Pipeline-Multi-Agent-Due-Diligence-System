"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { seedChecklist, updateChecklistItem } from "@/lib/api-client";
import type { ChecklistItemSummary } from "@/lib/workbench-data";

import styles from "./interactive.module.css";

const CHECKLIST_STATUSES = [
  "not_started",
  "in_progress",
  "satisfied",
  "waived",
  "blocked",
];

function labelize(value: string) {
  return value
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

export default function ChecklistPanel({
  caseId,
  items,
}: {
  caseId: string;
  items: ChecklistItemSummary[];
}) {
  const router = useRouter();
  const [seeding, setSeeding] = useState(false);
  const [seedResult, setSeedResult] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const satisfiedCount = items.filter((i) => i.status === "satisfied").length;
  const totalCount = items.length;
  const pct = totalCount > 0 ? Math.round((satisfiedCount / totalCount) * 100) : 0;

  // SVG coverage ring
  const radius = 28;
  const circumference = 2 * Math.PI * radius;
  const dashArray = (pct / 100) * circumference;

  async function handleSeed() {
    setSeeding(true);
    setError(null);
    setSeedResult(null);
    try {
      const result = await seedChecklist(caseId);
      setSeedResult(`Seeded ${result.seeded} checklist items`);
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Seed failed");
    } finally {
      setSeeding(false);
    }
  }

  async function handleStatusChange(itemId: string, newStatus: string) {
    try {
      await updateChecklistItem(caseId, itemId, { status: newStatus });
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Update failed");
    }
  }

  return (
    <div>
      <div className={styles.actionBar}>
        <button
          className={styles.btnPrimary}
          onClick={handleSeed}
          disabled={seeding}
        >
          {seeding ? "Seeding..." : "Seed Checklist"}
        </button>
        {seedResult && <span className={styles.successMsg}>{seedResult}</span>}
      </div>

      {error && <p className={styles.errorMsg}>{error}</p>}

      {totalCount > 0 && (
        <div className={styles.coverageRing}>
          <svg width="68" height="68" viewBox="0 0 68 68">
            <circle
              cx="34"
              cy="34"
              r={radius}
              fill="none"
              stroke="rgba(20, 36, 51, 0.08)"
              strokeWidth="6"
            />
            <circle
              cx="34"
              cy="34"
              r={radius}
              fill="none"
              stroke="var(--accent)"
              strokeWidth="6"
              strokeLinecap="round"
              strokeDasharray={`${dashArray} ${circumference}`}
              transform="rotate(-90 34 34)"
            />
          </svg>
          <div>
            <div className={styles.ringValue}>{pct}%</div>
            <div className={styles.ringLabel}>
              {satisfiedCount}/{totalCount} satisfied
            </div>
          </div>
        </div>
      )}

      {items.length === 0 ? (
        <p style={{ color: "var(--muted)", padding: "18px" }}>
          No checklist items yet. Seed the checklist from pack templates.
        </p>
      ) : (
        items.map((item) => (
          <div key={item.id} style={{ padding: "10px 0" }}>
            <div style={{ marginBottom: 6 }}>
              <strong>
                {item.mandatory && "* "}
                {item.title}
              </strong>
              <p style={{ color: "var(--muted)", fontSize: "0.88rem" }}>
                {item.detail}
              </p>
              {item.note && (
                <p style={{ color: "var(--accent-dark)", fontSize: "0.82rem" }}>
                  {item.note}
                </p>
              )}
            </div>
            <div className={styles.inlineEdit}>
              <select
                className={styles.inlineSelect}
                value={item.status}
                onChange={(e) => handleStatusChange(item.id, e.target.value)}
              >
                {CHECKLIST_STATUSES.map((s) => (
                  <option key={s} value={s}>
                    {labelize(s)}
                  </option>
                ))}
              </select>
              <span style={{ fontSize: "0.78rem", color: "var(--muted)" }}>
                {labelize(item.workstream_domain)}
              </span>
            </div>
          </div>
        ))
      )}
    </div>
  );
}
