"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { createExportPackage, createRun, getLlmProviders } from "@/lib/api-client";
import type { LlmProviderSummary } from "@/lib/workbench-data";

import styles from "./interactive.module.css";

type ReportTemplate = "standard" | "lender" | "board_memo" | "one_pager";

export default function RunWorkflowButton({ caseId }: { caseId: string }) {
  const router = useRouter();
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [note, setNote] = useState("");
  const [reportTemplate, setReportTemplate] = useState<ReportTemplate>("standard");
  const [providers, setProviders] = useState<LlmProviderSummary[]>([]);
  const [providerError, setProviderError] = useState<string | null>(null);
  const [loadingProviders, setLoadingProviders] = useState(false);
  const [llmProviderOverride, setLlmProviderOverride] = useState("");
  const [llmModelOverride, setLlmModelOverride] = useState("");

  useEffect(() => {
    async function loadProviders() {
      if (!showForm || providers.length > 0 || loadingProviders) {
        return;
      }
      setLoadingProviders(true);
      setProviderError(null);
      try {
        setProviders(await getLlmProviders());
      } catch (err) {
        setProviderError(
          err instanceof Error ? err.message : "Could not load LLM provider options.",
        );
      } finally {
        setLoadingProviders(false);
      }
    }

    void loadProviders();
  }, [loadingProviders, providers.length, showForm]);

  const openRouterProvider = providers.find((item) => item.provider === "openrouter");
  const openRouterModels = openRouterProvider?.models ?? [];

  async function handleRun(e: React.FormEvent) {
    e.preventDefault();
    setPending(true);
    setError(null);
    try {
      const result = await createRun(caseId, {
        requested_by: "Workbench Analyst",
        note: note.trim() || undefined,
        report_template: reportTemplate,
        llm_provider_override: llmProviderOverride || undefined,
        llm_model_override: llmModelOverride || undefined,
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
      setLlmProviderOverride("");
      setLlmModelOverride("");
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
      <div className={styles.field}>
        <label className={styles.fieldLabel}>LLM Runtime Override</label>
        <select
          className={styles.select}
          value={llmProviderOverride}
          onChange={(e) => {
            const value = e.target.value;
            setLlmProviderOverride(value);
            if (value !== "openrouter") {
              setLlmModelOverride("");
            }
          }}
        >
          <option value="">System default</option>
          <option value="none">Deterministic fallback</option>
          {providers
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
        <p className={styles.helpText}>
          {loadingProviders
            ? "Loading provider options..."
            : providerError ??
              "Leave this on System default to use the org default or environment fallback."}
        </p>
      </div>
      {llmProviderOverride === "openrouter" && (
        <div className={styles.field}>
          <label className={styles.fieldLabel}>OpenRouter Model Override</label>
          <select
            className={styles.select}
            value={llmModelOverride}
            onChange={(e) => setLlmModelOverride(e.target.value)}
          >
            <option value="">Use default OpenRouter model</option>
            {openRouterModels.map((model) => (
              <option key={model.model_id} value={model.model_id}>
                {model.label}
              </option>
            ))}
          </select>
          <p className={styles.helpText}>
            {openRouterProvider?.detail ??
              "Model choices come from the cached OpenRouter catalog."}
          </p>
        </div>
      )}
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
