import Link from "next/link";

import StatusControlCenter from "@/components/StatusControlCenter";

import styles from "../workbench.module.css";
import { getStatusWorkspace, labelize } from "../../lib/workbench-data";

export default async function StatusPage() {
  const workspace = await getStatusWorkspace();
  const { overview, dependencyReport, llmProviders, llmDefault, isFallback } = workspace;

  return (
    <div className={styles.page}>
      <div className={styles.auraLeft} />
      <div className={styles.auraRight} />
      <main className={styles.main}>
        <section className={styles.topBar}>
          <div className={styles.brandBlock}>
            <div className={styles.breadcrumb}>
              <Link href="/">Workbench</Link>
              <span>/</span>
              <span>Status</span>
            </div>
            <p className={styles.subtle}>
              Runtime status center for infrastructure, connectors, and LLM controls.
            </p>
          </div>
          <div className={styles.pillRow}>
            <span className={styles.pill}>{labelize(overview.current_phase)}</span>
            <span className={styles.pillMuted}>{labelize(dependencyReport.status)}</span>
            {isFallback ? (
              <span className={styles.pillWarning}>Demo fallback</span>
            ) : (
              <span className={styles.pillMuted}>Live API</span>
            )}
          </div>
        </section>

        <section className={styles.hero}>
          <span className={styles.eyebrow}>Runtime Control Center</span>
          <h1>Track dependency health and manage the default LLM runtime.</h1>
          <p className={styles.lead}>
            This surface shows the latest dependency status snapshots, the org
            default LLM runtime, and the currently available OpenRouter model
            catalog used by the run trigger.
          </p>
          <div className={styles.heroMeta}>
            <div className={styles.metaCard}>
              <span className={styles.metaLabel}>Environment</span>
              <strong>{dependencyReport.environment}</strong>
            </div>
            <div className={styles.metaCard}>
              <span className={styles.metaLabel}>Dependencies</span>
              <strong>{dependencyReport.dependencies.length}</strong>
            </div>
            <div className={styles.metaCard}>
              <span className={styles.metaLabel}>Org default</span>
              <strong>
                {llmDefault.llm_provider
                  ? `${labelize(llmDefault.llm_provider)}${
                      llmDefault.llm_model ? ` / ${llmDefault.llm_model}` : ""
                    }`
                  : "Deterministic"}
              </strong>
            </div>
            <div className={styles.metaCard}>
              <span className={styles.metaLabel}>Provider catalogs</span>
              <strong>{llmProviders.length}</strong>
            </div>
          </div>
        </section>

        <StatusControlCenter
          initialDependencyReport={dependencyReport}
          initialProviders={llmProviders}
          initialLlmDefault={llmDefault}
        />
      </main>
    </div>
  );
}
