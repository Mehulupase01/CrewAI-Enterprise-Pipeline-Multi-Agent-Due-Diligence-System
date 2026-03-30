"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { createCase } from "@/lib/api-client";

import styles from "./interactive.module.css";

const MOTION_PACKS = [
  "buy_side_diligence",
  "credit_lending",
  "vendor_onboarding",
];

const SECTOR_PACKS = [
  "tech_saas_services",
  "manufacturing_industrials",
  "bfsi_nbfc",
];

function labelize(value: string) {
  return value
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

export default function CreateCaseModal({
  onClose,
}: {
  onClose: () => void;
}) {
  const router = useRouter();
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [name, setName] = useState("");
  const [targetName, setTargetName] = useState("");
  const [motionPack, setMotionPack] = useState(MOTION_PACKS[0]);
  const [sectorPack, setSectorPack] = useState(SECTOR_PACKS[0]);
  const [summary, setSummary] = useState("");

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim() || !targetName.trim()) return;
    setPending(true);
    setError(null);
    try {
      const created = await createCase({
        name: name.trim(),
        target_name: targetName.trim(),
        motion_pack: motionPack,
        sector_pack: sectorPack,
        summary: summary.trim() || undefined,
      });
      router.push(`/cases/${created.id}`);
      router.refresh();
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create case");
    } finally {
      setPending(false);
    }
  }

  return (
    <div className={styles.overlay} onClick={onClose}>
      <form
        className={styles.modal}
        onClick={(e) => e.stopPropagation()}
        onSubmit={handleSubmit}
      >
        <h2 className={styles.modalTitle}>Create New Case</h2>

        <div className={styles.fieldGroup}>
          <div className={styles.field}>
            <label className={styles.fieldLabel}>Case Name</label>
            <input
              className={styles.input}
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Alpha Nimbus Acquisition"
              required
            />
          </div>

          <div className={styles.field}>
            <label className={styles.fieldLabel}>Target Name</label>
            <input
              className={styles.input}
              type="text"
              value={targetName}
              onChange={(e) => setTargetName(e.target.value)}
              placeholder="e.g. Nimbus Data Systems"
              required
            />
          </div>

          <div className={styles.field}>
            <label className={styles.fieldLabel}>Motion Pack</label>
            <select
              className={styles.select}
              value={motionPack}
              onChange={(e) => setMotionPack(e.target.value)}
            >
              {MOTION_PACKS.map((pack) => (
                <option key={pack} value={pack}>
                  {labelize(pack)}
                </option>
              ))}
            </select>
          </div>

          <div className={styles.field}>
            <label className={styles.fieldLabel}>Sector Pack</label>
            <select
              className={styles.select}
              value={sectorPack}
              onChange={(e) => setSectorPack(e.target.value)}
            >
              {SECTOR_PACKS.map((pack) => (
                <option key={pack} value={pack}>
                  {labelize(pack)}
                </option>
              ))}
            </select>
          </div>

          <div className={styles.field}>
            <label className={styles.fieldLabel}>Summary (optional)</label>
            <textarea
              className={styles.textarea}
              value={summary}
              onChange={(e) => setSummary(e.target.value)}
              placeholder="Brief description of the diligence case..."
            />
          </div>
        </div>

        {error && <p className={styles.errorMsg}>{error}</p>}

        <div className={styles.btnRow}>
          <button
            type="button"
            className={styles.btnSecondary}
            onClick={onClose}
            disabled={pending}
          >
            Cancel
          </button>
          <button
            type="submit"
            className={styles.btnPrimary}
            disabled={pending || !name.trim() || !targetName.trim()}
          >
            {pending ? "Creating..." : "Create Case"}
          </button>
        </div>
      </form>
    </div>
  );
}
