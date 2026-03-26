import styles from "./page.module.css";

const caseSummary = {
  name: "Alpha Nimbus Acquisition",
  target: "Nimbus Data Systems",
  motionPack: "Buy-side diligence",
  sectorPack: "Tech / SaaS / Services",
  phase: "Phase 2 evidence layer + completeness controls",
};

const documentQueue = [
  ["FY25 audited financials", "Received", "Uploaded data room"],
  ["Board minutes Q4 FY25", "Staged", "Management response"],
  ["MCA filing export", "Ready", "Public registry"],
];

const evidenceLedger = [
  ["Deferred revenue reconciliation", "Financial QoE", "0.91 confidence"],
  ["Director charge filing note", "Legal / Corporate", "Registry-linked"],
  ["GST notice summary", "Tax", "Flag candidate detected"],
];

const issueRegister = [
  [
    "Outstanding tax or GST exposure",
    "High severity",
    "Created from evidence scan",
  ],
  [
    "Unreconciled deferred revenue movement",
    "High severity",
    "Analyst-authored issue",
  ],
  [
    "Customer concentration risk",
    "Medium severity",
    "Awaiting commercial review",
  ],
];

const checklistCoverage = [
  ["Financial QoE", "2 of 3 complete", "Open monthly bridge follow-up"],
  ["Legal / Corporate", "1 of 2 complete", "Charge release still pending"],
  ["Tax", "1 of 1 complete", "GST notice triaged"],
  ["Cyber / Privacy", "0 of 1 complete", "DPDP controls review queued"],
];

const approvalSnapshot = [
  ["Latest review", "Changes requested", "High-severity tax issue still open"],
  ["Export readiness", "Blocked", "Mandatory checklist still incomplete"],
  ["Memo status", "Draft preview", "Executive memo can be generated for review"],
];

const trackerItems = [
  ["Request list", "Monthly churn bridge and customer cohorts", "Open"],
  ["Q&A", "Why implementation revenue spiked in Q3 FY25", "Answered"],
  ["Reviewer gate", "Approval not yet opened", "Pending"],
];

const adapterCatalog = [
  ["Uploaded data room", "Primary intake path", "Live"],
  ["MCA public records", "India corporate enrichment", "Fallback / exports"],
  ["Vendor connector", "Commercial data slot", "Fixture-backed"],
];

const completedLayers = [
  "Database-backed case operations and relationship models",
  "Document upload, parsing, storage, and evidence extraction",
  "Issue register endpoints and deterministic evidence-to-flag scan",
  "Pack-aware checklist templates and coverage summaries",
  "Deterministic approval review and executive memo generation",
  "Source-adapter catalog shaped for India and vendor readiness",
];

const nextBridge = [
  "Persist richer report bundles and exportable memo artifacts.",
  "Start the first buy-side diligence vertical slice over the evidence, issue, checklist, and approval core.",
  "Introduce agent-orchestrated workstream synthesis over the structured case state.",
];

const roadmap = [
  "Credit / lending pack reuses the same evidence, issue, and approval core.",
  "Vendor onboarding adds third-party risk and continuous screening workflows.",
  "Manufacturing and BFSI sector packs extend the rule layer, not the database core.",
];

export default function Home() {
  return (
    <div className={styles.page}>
      <div className={styles.auraLeft} />
      <div className={styles.auraRight} />
      <main className={styles.main}>
        <section className={styles.hero}>
          <span className={styles.kicker}>CrewAI Enterprise Pipeline</span>
          <h1>India due diligence, now tracking evidence, flags, and completeness.</h1>
          <p className={styles.lead}>
            The platform now ingests uploaded files, normalizes evidence,
            maintains live request and Q&amp;A trackers, turns risk signals into
            issue-register entries, and measures checklist coverage before a
            case can be treated as complete.
          </p>
          <div className={styles.heroMeta}>
            <div>
              <span className={styles.metaLabel}>Active case</span>
              <strong>{caseSummary.name}</strong>
            </div>
            <div>
              <span className={styles.metaLabel}>Target</span>
              <strong>{caseSummary.target}</strong>
            </div>
            <div>
              <span className={styles.metaLabel}>Current build</span>
              <strong>{caseSummary.phase}</strong>
            </div>
          </div>
        </section>

        <section className={styles.workspace}>
          <div className={styles.column}>
            <article className={styles.panel}>
              <div className={styles.panelHeader}>
                <span className={styles.badge}>Case record</span>
                <h2>Pack-aware control plane</h2>
              </div>
              <div className={styles.summaryCard}>
                <div>
                  <span className={styles.metaLabel}>Motion pack</span>
                  <strong>{caseSummary.motionPack}</strong>
                </div>
                <div>
                  <span className={styles.metaLabel}>Sector pack</span>
                  <strong>{caseSummary.sectorPack}</strong>
                </div>
                <div>
                  <span className={styles.metaLabel}>Country</span>
                  <strong>India</strong>
                </div>
              </div>
            </article>

            <article className={styles.panel}>
              <div className={styles.panelHeader}>
                <span className={styles.badge}>Artifacts</span>
                <h2>Document intake and processing queue</h2>
              </div>
              <div className={styles.table}>
                {documentQueue.map(([title, status, source]) => (
                  <div className={styles.row} key={title}>
                    <div>
                      <strong>{title}</strong>
                      <p>{source}</p>
                    </div>
                    <span className={styles.status}>{status}</span>
                  </div>
                ))}
              </div>
            </article>

            <article className={styles.panel}>
              <div className={styles.panelHeader}>
                <span className={styles.badge}>Evidence</span>
                <h2>Normalized diligence ledger</h2>
              </div>
              <div className={styles.table}>
                {evidenceLedger.map(([title, workstream, note]) => (
                  <div className={styles.row} key={title}>
                    <div>
                      <strong>{title}</strong>
                      <p>{workstream}</p>
                    </div>
                    <span className={styles.note}>{note}</span>
                  </div>
                ))}
              </div>
            </article>

            <article className={styles.panel}>
              <div className={styles.panelHeader}>
                <span className={styles.badge}>Flags</span>
                <h2>Issue register and red-flag queue</h2>
              </div>
              <div className={styles.table}>
                {issueRegister.map(([title, severity, note]) => (
                  <div className={styles.row} key={title}>
                    <div>
                      <strong>{title}</strong>
                      <p>{note}</p>
                    </div>
                    <span className={styles.status}>{severity}</span>
                  </div>
                ))}
              </div>
            </article>
          </div>

          <div className={styles.column}>
            <article className={styles.panel}>
              <div className={styles.panelHeader}>
                <span className={styles.badge}>Coverage</span>
                <h2>Mandatory checklist completion</h2>
              </div>
              <div className={styles.table}>
                {checklistCoverage.map(([workstream, progress, note]) => (
                  <div className={styles.row} key={workstream}>
                    <div>
                      <strong>{workstream}</strong>
                      <p>{note}</p>
                    </div>
                    <span className={styles.status}>{progress}</span>
                  </div>
                ))}
              </div>
            </article>

            <article className={styles.panel}>
              <div className={styles.panelHeader}>
                <span className={styles.badge}>Review</span>
                <h2>Approval gate and memo readiness</h2>
              </div>
              <div className={styles.table}>
                {approvalSnapshot.map(([lane, status, note]) => (
                  <div className={styles.row} key={lane}>
                    <div>
                      <strong>{lane}</strong>
                      <p>{note}</p>
                    </div>
                    <span className={styles.status}>{status}</span>
                  </div>
                ))}
              </div>
            </article>

            <article className={styles.panel}>
              <div className={styles.panelHeader}>
                <span className={styles.badge}>Trackers</span>
                <h2>Request list, Q&amp;A, and approvals</h2>
              </div>
              <div className={styles.table}>
                {trackerItems.map(([lane, item, status]) => (
                  <div className={styles.row} key={lane}>
                    <div>
                      <strong>{lane}</strong>
                      <p>{item}</p>
                    </div>
                    <span className={styles.status}>{status}</span>
                  </div>
                ))}
              </div>
            </article>

            <article className={styles.panel}>
              <div className={styles.panelHeader}>
                <span className={styles.badge}>Adapters</span>
                <h2>India evidence sources and expansion contracts</h2>
              </div>
              <div className={styles.table}>
                {adapterCatalog.map(([title, purpose, mode]) => (
                  <div className={styles.row} key={title}>
                    <div>
                      <strong>{title}</strong>
                      <p>{purpose}</p>
                    </div>
                    <span className={styles.note}>{mode}</span>
                  </div>
                ))}
              </div>
            </article>

            <article className={styles.panel}>
              <div className={styles.panelHeader}>
                <span className={styles.badge}>Roadmap</span>
                <h2>Expansion-ready by design</h2>
              </div>
              <ul className={styles.list}>
                {roadmap.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </article>
          </div>
        </section>

        <section className={styles.grid}>
          <article className={styles.panel}>
            <div className={styles.panelHeader}>
              <span className={styles.badge}>Completed</span>
              <h2>Verified platform layers</h2>
            </div>
            <ul className={styles.list}>
              {completedLayers.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </article>

          <article className={styles.panel}>
              <div className={styles.panelHeader}>
                <span className={styles.badge}>Next</span>
                <h2>Immediate build bridge</h2>
              </div>
              <ul className={styles.list}>
                {nextBridge.map((item) => (
                  <li key={item}>{item}</li>
              ))}
            </ul>
          </article>
        </section>
      </main>
    </div>
  );
}
