"use client";

import { useMemo, useState } from "react";

import {
  getDependencyStatuses,
  refreshDependencyStatuses,
  updateOrgLlmDefault,
} from "@/lib/api-client";
import type {
  DependencyStatusReport,
  LlmProviderSummary,
  OrgLlmRuntimeConfig,
} from "@/lib/workbench-data";

import interactiveStyles from "./interactive.module.css";
import styles from "../app/workbench.module.css";

type Props = {
  initialDependencyReport: DependencyStatusReport;
  initialProviders: LlmProviderSummary[];
  initialLlmDefault: OrgLlmRuntimeConfig;
};

export default function StatusControlCenter({
  initialDependencyReport,
  initialProviders,
  initialLlmDefault,
}: Props) {
  const [dependencyReport, setDependencyReport] = useState(initialDependencyReport);
  const [llmDefault, setLlmDefault] = useState(initialLlmDefault);
  const [providerValue, setProviderValue] = useState(initialLlmDefault.llm_provider ?? "");
  const [modelValue, setModelValue] = useState(initialLlmDefault.llm_model ?? "");
  const [refreshPending, setRefreshPending] = useState(false);
  const [savePending, setSavePending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const openRouterProvider = useMemo(
    () => initialProviders.find((provider) => provider.provider === "openrouter"),
    [initialProviders],
  );

  const dependencyCounts = useMemo(() => {
    return dependencyReport.dependencies.reduce(
      (acc, dependency) => {
        acc.total += 1;
        if (dependency.status === "ok") {
          acc.ok += 1;
        } else if (dependency.status === "degraded") {
          acc.degraded += 1;
        } else {
          acc.failed += 1;
        }
        return acc;
      },
      { total: 0, ok: 0, degraded: 0, failed: 0 },
    );
  }, [dependencyReport.dependencies]);

  async function handleRefresh() {
    setRefreshPending(true);
    setError(null);
    setSuccess(null);
    try {
      const report = await refreshDependencyStatuses();
      setDependencyReport(report);
      setSuccess("Dependency snapshots refreshed.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not refresh dependency status.");
      try {
        setDependencyReport(await getDependencyStatuses());
      } catch {
        // Keep the last known report if both refresh and fallback reload fail.
      }
    } finally {
      setRefreshPending(false);
    }
  }

  async function handleSaveDefault(e: React.FormEvent) {
    e.preventDefault();
    setSavePending(true);
    setError(null);
    setSuccess(null);
    try {
      const updated = await updateOrgLlmDefault({
        llm_provider: providerValue || null,
        llm_model: providerValue === "openrouter" ? modelValue || null : null,
      });
      setLlmDefault(updated);
      setProviderValue(updated.llm_provider ?? "");
      setModelValue(updated.llm_model ?? "");
      setSuccess("Org default runtime updated.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not update org default runtime.");
    } finally {
      setSavePending(false);
    }
  }

  return (
    <div className={styles.stack}>
      <article className={styles.panel}>
        <div className={styles.panelHeader}>
          <span className={styles.badge}>Summary</span>
          <h2>Runtime dependency pulse</h2>
        </div>
        <div className={styles.summaryGrid}>
          <div className={styles.summaryCard}>
            <span className={styles.metaLabel}>Dependencies</span>
            <strong>{dependencyCounts.total}</strong>
            <p>Latest persisted dependency snapshots.</p>
          </div>
          <div className={styles.summaryCard}>
            <span className={styles.metaLabel}>Healthy</span>
            <strong>{dependencyCounts.ok}</strong>
            <p>Dependencies currently reporting `ok`.</p>
          </div>
          <div className={styles.summaryCard}>
            <span className={styles.metaLabel}>Degraded</span>
            <strong>{dependencyCounts.degraded}</strong>
            <p>Dependencies that need review but are not hard-down.</p>
          </div>
          <div className={styles.summaryCard}>
            <span className={styles.metaLabel}>Failed</span>
            <strong>{dependencyCounts.failed}</strong>
            <p>Dependencies currently failing the runtime contract.</p>
          </div>
        </div>
      </article>

      <article className={styles.panel}>
        <div className={styles.panelHeader}>
          <span className={styles.badge}>Control</span>
          <h2>LLM default and dependency refresh</h2>
        </div>
        <form onSubmit={handleSaveDefault} style={{ display: "grid", gap: 12 }}>
          <div className={interactiveStyles.field}>
            <label className={interactiveStyles.fieldLabel}>Org Default Provider</label>
            <select
              className={interactiveStyles.select}
              value={providerValue}
              onChange={(event) => {
                const nextProvider = event.target.value;
                setProviderValue(nextProvider);
                if (nextProvider !== "openrouter") {
                  setModelValue("");
                }
              }}
            >
              <option value="">Deterministic fallback</option>
              {initialProviders
                .filter((provider) => provider.provider !== "none")
                .map((provider) => (
                  <option
                    key={provider.provider}
                    value={provider.provider}
                    disabled={!provider.available}
                  >
                    {provider.label}
                  </option>
                ))}
            </select>
            <p className={interactiveStyles.helpText}>
              {providerValue
                ? `Current default: ${llmDefault.llm_provider ?? "deterministic"}`
                : "Use the deterministic pipeline unless a run requests a live provider."}
            </p>
          </div>

          {providerValue === "openrouter" && (
            <div className={interactiveStyles.field}>
              <label className={interactiveStyles.fieldLabel}>Default OpenRouter Model</label>
              <select
                className={interactiveStyles.select}
                value={modelValue}
                onChange={(event) => setModelValue(event.target.value)}
              >
                <option value="">Use the first eligible OpenRouter model</option>
                {(openRouterProvider?.models ?? []).map((model) => (
                  <option key={model.model_id} value={model.model_id}>
                    {model.label}
                  </option>
                ))}
              </select>
              <p className={interactiveStyles.helpText}>
                {openRouterProvider?.detail ??
                  "OpenRouter model options are loaded from the cached provider catalog."}
              </p>
            </div>
          )}

          {(error || success) && (
            <p className={error ? interactiveStyles.errorMsg : interactiveStyles.successMsg}>
              {error ?? success}
            </p>
          )}

          <div className={interactiveStyles.btnRow}>
            <button
              type="button"
              className={interactiveStyles.btnSecondary}
              onClick={handleRefresh}
              disabled={refreshPending}
            >
              {refreshPending ? "Refreshing..." : "Refresh Dependencies"}
            </button>
            <button
              type="submit"
              className={interactiveStyles.btnPrimary}
              disabled={savePending}
            >
              {savePending ? "Saving..." : "Save Org Default"}
            </button>
          </div>
        </form>
      </article>

      <article className={styles.panel}>
        <div className={styles.panelHeader}>
          <span className={styles.badge}>Dependencies</span>
          <h2>Current runtime status</h2>
        </div>
        <div className={styles.table}>
          {dependencyReport.dependencies.map((dependency) => (
            <div className={styles.row} key={dependency.name}>
              <div>
                <strong>{dependency.name}</strong>
                <p>
                  {dependency.detail}
                </p>
                <p>
                  Category: {dependency.category} | Mode: {dependency.mode} | Last checked:{" "}
                  {new Date(dependency.last_checked_at).toLocaleString()}
                </p>
                <p>
                  Last success:{" "}
                  {dependency.last_success_at
                    ? new Date(dependency.last_success_at).toLocaleString()
                    : "No successful check recorded"}
                </p>
                {dependency.failure_reason && <p>Failure: {dependency.failure_reason}</p>}
              </div>
              <span className={styles.status}>
                {dependency.status} | {dependency.latency_ms.toFixed(1)} ms
              </span>
            </div>
          ))}
        </div>
      </article>
    </div>
  );
}
