import Link from "next/link";
import { notFound } from "next/navigation";

import ApprovalPanel from "@/components/ApprovalPanel";
import ChecklistPanel from "@/components/ChecklistPanel";
import DocumentUpload from "@/components/DocumentUpload";
import IssueManager from "@/components/IssueManager";
import RequestQaPanel from "@/components/RequestQaPanel";
import RunWorkflowButton from "@/components/RunWorkflowButton";

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
              <IssueManager caseId={caseId} issues={caseDetail.issues} />
            </article>

            <article className={styles.panel}>
              <div className={styles.panelHeader}>
                <span className={styles.badge}>Checklist</span>
                <h2>Mandatory completion controls</h2>
              </div>
              <ChecklistPanel caseId={caseId} items={caseDetail.checklist_items} />
            </article>
          </div>

          <div className={styles.stack}>
            <article className={styles.panel}>
              <div className={styles.panelHeader}>
                <span className={styles.badge}>Upload</span>
                <h2>Upload documents</h2>
              </div>
              <DocumentUpload caseId={caseId} />
            </article>

            <article className={styles.panel}>
              <div className={styles.panelHeader}>
                <span className={styles.badge}>Artifacts</span>
                <h2>Documents and evidence</h2>
              </div>
              <div className={styles.table}>
                {caseDetail.documents.length === 0 && caseDetail.evidence_items.length === 0 ? (
                  <p className={styles.empty}>No documents uploaded yet.</p>
                ) : (
                  <>
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
                  </>
                )}
              </div>
            </article>

            <article className={styles.panel}>
              <div className={styles.panelHeader}>
                <span className={styles.badge}>Review</span>
                <h2>Approval gate</h2>
              </div>
              <ApprovalPanel caseId={caseId} approvals={caseDetail.approvals} />
            </article>

            <article className={styles.panel}>
              <div className={styles.panelHeader}>
                <span className={styles.badge}>Runs</span>
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12 }}>
                  <h2>Execution history</h2>
                  <RunWorkflowButton caseId={caseId} />
                </div>
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
                <span className={styles.badge}>Requests &amp; Q&amp;A</span>
                <h2>Diligence asks and management responses</h2>
              </div>
              <RequestQaPanel
                caseId={caseId}
                requests={caseDetail.request_items}
                qaItems={caseDetail.qa_items}
              />
            </article>
          </div>
        </section>
      </main>
    </div>
  );
}
