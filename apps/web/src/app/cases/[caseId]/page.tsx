import Link from "next/link";
import { notFound } from "next/navigation";

import styles from "../../workbench.module.css";
import {
  getCaseWorkspace,
  labelize,
  summarizeCase,
} from "../../../lib/workbench-data";

type PageProps = {
  params: Promise<{ caseId: string }>;
};

export default async function CasePage({ params }: PageProps) {
  const { caseId } = await params;
  const workspace = await getCaseWorkspace(caseId);
  if (workspace === null) {
    notFound();
  }

  const { caseDetail, runs, isFallback } = workspace;
  const caseSummary = summarizeCase(caseDetail);

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
              <span>{caseDetail.name}</span>
            </div>
            <p className={styles.subtle}>
              Detailed case workspace for analyst review and reviewer sign-off.
            </p>
          </div>
          <div className={styles.pillRow}>
            <span className={styles.pill}>{labelize(caseDetail.status)}</span>
            <span className={styles.pillMuted}>{labelize(caseDetail.motion_pack)}</span>
            {isFallback ? (
              <span className={styles.pillWarning}>Demo fallback</span>
            ) : (
              <span className={styles.pillMuted}>Live API</span>
            )}
          </div>
        </section>

        <section className={styles.hero}>
          <span className={styles.eyebrow}>Case Workspace</span>
          <h1>{caseDetail.name}</h1>
          <p className={styles.lead}>
            {caseDetail.summary ??
              "Case summary has not been written yet. The workspace below still exposes the underlying diligence state."}
          </p>
          <div className={styles.heroMeta}>
            <div className={styles.metaCard}>
              <span className={styles.metaLabel}>Target</span>
              <strong>{caseDetail.target_name}</strong>
            </div>
            <div className={styles.metaCard}>
              <span className={styles.metaLabel}>Sector pack</span>
              <strong>{labelize(caseDetail.sector_pack)}</strong>
            </div>
            <div className={styles.metaCard}>
              <span className={styles.metaLabel}>Approval state</span>
              <strong>{caseSummary.approvalState}</strong>
            </div>
          </div>
        </section>

        <section className={styles.workspace}>
          <div className={styles.stack}>
            <article className={styles.panel}>
              <div className={styles.panelHeader}>
                <span className={styles.badge}>Pulse</span>
                <h2>Case status at a glance</h2>
              </div>
              <div className={styles.kpiGrid}>
                <div className={styles.kpiCard}>
                  <span className={styles.metaLabel}>Documents</span>
                  <strong>{caseSummary.documentCount}</strong>
                  <p className={styles.caption}>Uploaded and parsed artifacts</p>
                </div>
                <div className={styles.kpiCard}>
                  <span className={styles.metaLabel}>Evidence</span>
                  <strong>{caseSummary.evidenceCount}</strong>
                  <p className={styles.caption}>Normalized evidence items</p>
                </div>
                <div className={styles.kpiCard}>
                  <span className={styles.metaLabel}>Issues</span>
                  <strong>{caseSummary.issueCount}</strong>
                  <p className={styles.caption}>Tracked issue-register items</p>
                </div>
                <div className={styles.kpiCard}>
                  <span className={styles.metaLabel}>Open requests</span>
                  <strong>{caseSummary.openRequestCount}</strong>
                  <p className={styles.caption}>Outstanding diligence asks</p>
                </div>
              </div>
            </article>

            <article className={styles.panel}>
              <div className={styles.panelHeader}>
                <span className={styles.badge}>Issues</span>
                <h2>Issue register</h2>
              </div>
              <div className={styles.table}>
                {caseDetail.issues.length === 0 ? (
                  <p className={styles.empty}>No issues have been registered yet.</p>
                ) : (
                  caseDetail.issues.map((issue) => (
                    <div className={styles.row} key={issue.id}>
                      <div>
                        <strong>{issue.title}</strong>
                        <p>{issue.business_impact}</p>
                        <p>{issue.recommended_action ?? "Triage still pending."}</p>
                      </div>
                      <span className={styles.status}>
                        {labelize(issue.severity)}
                      </span>
                    </div>
                  ))
                )}
              </div>
            </article>

            <article className={styles.panel}>
              <div className={styles.panelHeader}>
                <span className={styles.badge}>Checklist</span>
                <h2>Mandatory completion controls</h2>
              </div>
              <div className={styles.table}>
                {caseDetail.checklist_items.length === 0 ? (
                  <p className={styles.empty}>Checklist templates have not been seeded yet.</p>
                ) : (
                  caseDetail.checklist_items.map((item) => (
                    <div className={styles.row} key={item.id}>
                      <div>
                        <strong>{item.title}</strong>
                        <p>{item.detail}</p>
                        <p>{item.note ?? "No analyst note yet."}</p>
                      </div>
                      <span className={styles.status}>
                        {labelize(item.status)}
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
                <span className={styles.badge}>Artifacts</span>
                <h2>Documents and evidence</h2>
              </div>
              <div className={styles.table}>
                {caseDetail.documents.map((document) => (
                  <div className={styles.row} key={document.id}>
                    <div>
                      <strong>{document.title}</strong>
                      <p>{labelize(document.source_kind)}</p>
                      <p>{document.original_filename ?? "No filename available."}</p>
                    </div>
                    <span className={styles.note}>
                      {labelize(document.processing_status)}
                    </span>
                  </div>
                ))}
                {caseDetail.evidence_items.map((evidence) => (
                  <div className={styles.row} key={evidence.id}>
                    <div>
                      <strong>{evidence.title}</strong>
                      <p>{evidence.citation}</p>
                      <p>{evidence.excerpt}</p>
                    </div>
                    <span className={styles.note}>
                      {labelize(evidence.workstream_domain)}
                    </span>
                  </div>
                ))}
              </div>
            </article>

            <article className={styles.panel}>
              <div className={styles.panelHeader}>
                <span className={styles.badge}>Review</span>
                <h2>Approvals and open asks</h2>
              </div>
              <div className={styles.table}>
                {caseDetail.approvals.length === 0 ? (
                  <p className={styles.empty}>No approval reviews have been recorded yet.</p>
                ) : (
                  caseDetail.approvals.map((approval) => (
                    <div className={styles.row} key={approval.id}>
                      <div>
                        <strong>{approval.reviewer}</strong>
                        <p>{approval.rationale}</p>
                        <p>{approval.note ?? "No reviewer note."}</p>
                      </div>
                      <span className={styles.status}>
                        {labelize(approval.decision)}
                      </span>
                    </div>
                  ))
                )}
                {caseDetail.request_items.map((request) => (
                  <div className={styles.row} key={request.id}>
                    <div>
                      <strong>{request.title}</strong>
                      <p>{request.detail}</p>
                      <p>{request.owner ?? "No owner assigned."}</p>
                    </div>
                    <span className={styles.note}>
                      {labelize(request.status)}
                    </span>
                  </div>
                ))}
              </div>
            </article>

            <article className={styles.panel}>
              <div className={styles.panelHeader}>
                <span className={styles.badge}>Runs</span>
                <h2>Execution history</h2>
              </div>
              <div className={styles.table}>
                {runs.length === 0 ? (
                  <p className={styles.empty}>No workflow runs have been executed yet.</p>
                ) : (
                  runs.map((run) => (
                    <Link
                      className={styles.rowLink}
                      href={`/cases/${caseDetail.id}/runs/${run.id}`}
                      key={run.id}
                    >
                      <div>
                        <strong>{run.requested_by}</strong>
                        <p>{run.summary ?? "No run summary available."}</p>
                        <p>{run.note ?? "No operator note."}</p>
                      </div>
                      <span className={styles.status}>
                        {labelize(run.status)}
                      </span>
                    </Link>
                  ))
                )}
              </div>
            </article>

            <article className={styles.panel}>
              <div className={styles.panelHeader}>
                <span className={styles.badge}>Q&amp;A</span>
                <h2>Management responses</h2>
              </div>
              <div className={styles.table}>
                {caseDetail.qa_items.length === 0 ? (
                  <p className={styles.empty}>No Q&amp;A items have been captured yet.</p>
                ) : (
                  caseDetail.qa_items.map((item) => (
                    <div className={styles.row} key={item.id}>
                      <div>
                        <strong>{item.question}</strong>
                        <p>{item.response ?? "Awaiting response."}</p>
                        <p>{item.requested_by ?? "No requester listed."}</p>
                      </div>
                      <span className={styles.note}>{labelize(item.status)}</span>
                    </div>
                  ))
                )}
              </div>
            </article>
          </div>
        </section>
      </main>
    </div>
  );
}
