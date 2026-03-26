import Link from "next/link";
import { notFound } from "next/navigation";

import styles from "../../../../workbench.module.css";
import {
  getRunWorkspace,
  labelize,
  summarizeRun,
} from "../../../../../lib/workbench-data";

type PageProps = {
  params: Promise<{ caseId: string; runId: string }>;
};

export default async function RunPage({ params }: PageProps) {
  const { caseId, runId } = await params;
  const workspace = await getRunWorkspace(caseId, runId);
  if (workspace === null) {
    notFound();
  }

  const { caseDetail, run, isFallback } = workspace;
  const runSummary = summarizeRun(run);

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
              <Link href={`/cases/${caseDetail.id}`}>{caseDetail.name}</Link>
              <span>/</span>
              <span>{run.id}</span>
            </div>
            <p className={styles.subtle}>
              Run viewer for traces, workstream syntheses, and generated bundles.
            </p>
          </div>
          <div className={styles.pillRow}>
            <span className={styles.pill}>{labelize(run.status)}</span>
            {isFallback ? (
              <span className={styles.pillWarning}>Demo fallback</span>
            ) : (
              <span className={styles.pillMuted}>Live API</span>
            )}
          </div>
        </section>

        <section className={styles.hero}>
          <span className={styles.eyebrow}>Workflow Run</span>
          <h1>{run.id}</h1>
          <p className={styles.lead}>
            {run.summary ?? "This run completed without a stored summary."}
          </p>
          <div className={styles.heroMeta}>
            <div className={styles.metaCard}>
              <span className={styles.metaLabel}>Requested by</span>
              <strong>{run.requested_by}</strong>
            </div>
            <div className={styles.metaCard}>
              <span className={styles.metaLabel}>Trace events</span>
              <strong>{runSummary.traceCount}</strong>
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
                <span className={styles.badge}>Trace</span>
                <h2>Execution trace</h2>
              </div>
              <div className={styles.table}>
                {run.trace_events.map((event) => (
                  <div className={styles.row} key={event.id}>
                    <div>
                      <strong>
                        {event.sequence_number}. {event.title}
                      </strong>
                      <p>{event.message}</p>
                      <p>{labelize(event.step_key)}</p>
                    </div>
                    <span className={styles.note}>{labelize(event.level)}</span>
                  </div>
                ))}
              </div>
            </article>

            <article className={styles.panel}>
              <div className={styles.panelHeader}>
                <span className={styles.badge}>Synthesis</span>
                <h2>Workstream outputs</h2>
              </div>
              <div className={styles.table}>
                {run.workstream_syntheses.length === 0 ? (
                  <p className={styles.empty}>No workstream syntheses were stored for this run.</p>
                ) : (
                  run.workstream_syntheses.map((synthesis) => (
                    <div className={styles.row} key={synthesis.id}>
                      <div>
                        <strong>{labelize(synthesis.workstream_domain)}</strong>
                        <p>{synthesis.headline}</p>
                        <p>{synthesis.recommended_next_action}</p>
                      </div>
                      <span className={styles.status}>
                        {labelize(synthesis.status)}
                      </span>
                    </div>
                  ))
                )}
              </div>
            </article>
          </div>

          <div className={styles.stack}>
            <article className={styles.panel}>
              <div className={styles.panelHeader}>
                <span className={styles.badge}>Bundles</span>
                <h2>Generated report artifacts</h2>
              </div>
              <div className={styles.stack}>
                {run.report_bundles.map((bundle) => (
                  <article className={styles.previewCard} key={bundle.id}>
                    <header>
                      <div>
                        <strong>{bundle.title}</strong>
                        <p className={styles.caption}>
                          {bundle.summary ?? "No summary available."}
                        </p>
                      </div>
                      <span className={styles.note}>
                        {labelize(bundle.bundle_kind)}
                      </span>
                    </header>
                    <pre className={styles.codePreview}>
                      {bundle.content}
                    </pre>
                  </article>
                ))}
              </div>
            </article>

            <article className={styles.panel}>
              <div className={styles.panelHeader}>
                <span className={styles.badge}>Context</span>
                <h2>Run context</h2>
              </div>
              <div className={styles.summaryGrid}>
                <div className={styles.summaryCard}>
                  <span className={styles.metaLabel}>Case</span>
                  <strong>{caseDetail.name}</strong>
                  <p>{caseDetail.target_name}</p>
                </div>
                <div className={styles.summaryCard}>
                  <span className={styles.metaLabel}>Operator note</span>
                  <strong>{run.note ?? "No note"}</strong>
                  <p>Stored with the workflow run request.</p>
                </div>
                <div className={styles.summaryCard}>
                  <span className={styles.metaLabel}>Syntheses</span>
                  <strong>{runSummary.synthesisCount}</strong>
                  <p>Domain-level outputs stored on this run.</p>
                </div>
              </div>
              <Link
                className={styles.rowLink}
                href={`/cases/${caseDetail.id}`}
              >
                <div>
                  <strong>Return to case workspace</strong>
                  <p>
                    Move back to the full case view for issues, checklists,
                    requests, and additional run history.
                  </p>
                </div>
                <span className={styles.note}>Back to case</span>
              </Link>
            </article>
          </div>
        </section>
      </main>
    </div>
  );
}
