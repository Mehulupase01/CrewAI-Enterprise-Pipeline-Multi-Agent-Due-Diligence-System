import Link from "next/link";

import CreateCaseButton from "@/components/CreateCaseButton";

import styles from "./workbench.module.css";
import {
  getDashboardData,
  labelize,
  summarizeCase,
  summarizeRun,
} from "../lib/workbench-data";

export default async function Home() {
  const { overview, cases, featuredCase, latestRun, isFallback } =
    await getDashboardData();
  const caseSummary = summarizeCase(featuredCase);
  const runSummary = summarizeRun(latestRun);

  return (
    <div className={styles.page}>
      <div className={styles.auraLeft} />
      <div className={styles.auraRight} />
      <main className={styles.main}>
        <section className={styles.topBar}>
          <div className={styles.brandBlock}>
            <span className={styles.eyebrow}>CrewAI Enterprise Pipeline</span>
            <p className={styles.subtle}>
              Analyst workbench for the India diligence operating system.
            </p>
          </div>
          <div className={styles.pillRow}>
            <span className={styles.pill}>
              {labelize(overview.current_phase)}
            </span>
            <span className={styles.pillMuted}>{overview.country}</span>
            {isFallback ? (
              <span className={styles.pillWarning}>Demo fallback</span>
            ) : (
              <span className={styles.pillMuted}>Live API</span>
            )}
          </div>
        </section>

        <section className={styles.hero}>
          <span className={styles.eyebrow}>Interactive Workbench</span>
          <h1>Create, manage, and run diligence cases end-to-end.</h1>
          <p className={styles.lead}>
            Full analyst workbench with case creation, document upload, issue
            management, checklist toggling, approval workflows, and live
            run streaming. Step into any case to start working.
          </p>
          <div className={styles.heroMeta}>
            <div className={styles.metaCard}>
              <span className={styles.metaLabel}>Featured case</span>
              <strong>{featuredCase.name}</strong>
            </div>
            <div className={styles.metaCard}>
              <span className={styles.metaLabel}>Latest run</span>
              <strong>{labelize(latestRun.status)}</strong>
            </div>
            <div className={styles.metaCard}>
              <span className={styles.metaLabel}>Report bundles</span>
              <strong>{runSummary.bundleCount}</strong>
            </div>
          </div>
        </section>

        <section className={styles.workspace}>
          <div className={styles.stack}>
            <article className={styles.panel}>
              <div className={styles.panelHeader}>
                <span className={styles.badge}>Cases</span>
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12 }}>
                  <h2>Case workspace entry points</h2>
                  <CreateCaseButton />
                </div>
              </div>
              <div className={styles.cardGrid}>
                {cases.map((caseItem) => (
                  <Link
                    className={styles.rowLink}
                    href={`/cases/${caseItem.id}`}
                    key={caseItem.id}
                  >
                    <div>
                      <strong>{caseItem.name}</strong>
                      <p>{caseItem.target_name}</p>
                      <p>{caseItem.summary ?? "No summary available yet."}</p>
                    </div>
                    <span className={styles.status}>
                      {labelize(caseItem.status)}
                    </span>
                  </Link>
                ))}
              </div>
            </article>

            <article className={styles.panel}>
              <div className={styles.panelHeader}>
                <span className={styles.badge}>Featured</span>
                <h2>Current case pulse</h2>
              </div>
              <div className={styles.kpiGrid}>
                <div className={styles.kpiCard}>
                  <span className={styles.metaLabel}>Issues</span>
                  <strong>{caseSummary.issueCount}</strong>
                  <p className={styles.caption}>Tracked items in the issue register</p>
                </div>
                <div className={styles.kpiCard}>
                  <span className={styles.metaLabel}>High blockers</span>
                  <strong>{caseSummary.blockingIssueCount}</strong>
                  <p className={styles.caption}>Critical or high-severity items</p>
                </div>
                <div className={styles.kpiCard}>
                  <span className={styles.metaLabel}>Evidence</span>
                  <strong>{caseSummary.evidenceCount}</strong>
                  <p className={styles.caption}>Normalized evidence ledger items</p>
                </div>
                <div className={styles.kpiCard}>
                  <span className={styles.metaLabel}>Open requests</span>
                  <strong>{caseSummary.openRequestCount}</strong>
                  <p className={styles.caption}>Outstanding diligence asks</p>
                </div>
              </div>
              <Link
                className={styles.rowLink}
                href={`/cases/${featuredCase.id}`}
              >
                <div>
                  <strong>Open case workspace</strong>
                  <p>
                    Review documents, issues, checklist coverage, approvals,
                    and run history for {featuredCase.target_name}.
                  </p>
                </div>
                <span className={styles.note}>Go to case</span>
              </Link>
            </article>
          </div>

          <div className={styles.stack}>
            <article className={styles.panel}>
              <div className={styles.panelHeader}>
                <span className={styles.badge}>Platform</span>
                <h2>Pack-aware operating surface</h2>
              </div>
              <div className={styles.summaryGrid}>
                <div className={styles.summaryCard}>
                  <span className={styles.metaLabel}>Motion packs</span>
                  <strong>{overview.motion_packs.length}</strong>
                  <p>{overview.motion_packs.map(labelize).join(", ")}</p>
                </div>
                <div className={styles.summaryCard}>
                  <span className={styles.metaLabel}>Sector packs</span>
                  <strong>{overview.sector_packs.length}</strong>
                  <p>{overview.sector_packs.map(labelize).join(", ")}</p>
                </div>
                <div className={styles.summaryCard}>
                  <span className={styles.metaLabel}>Workstreams</span>
                  <strong>{overview.workstream_domains.length}</strong>
                  <p>{overview.workstream_domains.map(labelize).join(", ")}</p>
                </div>
              </div>
              <Link className={styles.rowLink} href="/status">
                <div>
                  <strong>Open runtime status center</strong>
                  <p>
                    Inspect dependency health, connector posture, and current LLM
                    runtime defaults from the workbench.
                  </p>
                </div>
                <span className={styles.note}>Go to status</span>
              </Link>
            </article>

            <article className={styles.panel}>
              <div className={styles.panelHeader}>
                <span className={styles.badge}>Runs</span>
                <h2>Latest workflow execution</h2>
              </div>
              <div className={styles.table}>
                <div className={styles.row}>
                  <div>
                    <strong>Run status</strong>
                    <p>{latestRun.summary ?? "No run summary available."}</p>
                  </div>
                  <span className={styles.status}>
                    {labelize(latestRun.status)}
                  </span>
                </div>
                <div className={styles.row}>
                  <div>
                    <strong>Trace events</strong>
                    <p>Execution audit trail stored for this run.</p>
                  </div>
                  <span className={styles.note}>{runSummary.traceCount}</span>
                </div>
                <div className={styles.row}>
                  <div>
                    <strong>Workstream syntheses</strong>
                    <p>Persisted domain-level diligence summaries.</p>
                  </div>
                  <span className={styles.note}>{runSummary.synthesisCount}</span>
                </div>
              </div>
              <Link
                className={styles.rowLink}
                href={`/cases/${featuredCase.id}/runs/${latestRun.id}`}
              >
                <div>
                  <strong>Open run viewer</strong>
                  <p>
                    Inspect trace events, report bundles, and workstream
                    syntheses for the latest execution.
                  </p>
                </div>
                <span className={styles.note}>Go to run</span>
              </Link>
            </article>
          </div>
        </section>
      </main>
    </div>
  );
}
