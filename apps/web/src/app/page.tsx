import styles from "./page.module.css";

const caseSummary = {
  name: "Alpha Nimbus Acquisition",
  target: "Nimbus Data Systems",
  motionPack: "Buy-side diligence",
  sectorPack: "Tech / SaaS / Services",
  phase: "Phase 2 operations layer",
};

const documentQueue = [
  ["FY25 audited financials", "Received", "Uploaded data room"],
  ["Board minutes Q4 FY25", "Staged", "Management response"],
  ["MCA filing export", "Ready", "Public registry"],
];

const evidenceLedger = [
  ["Deferred revenue reconciliation", "Financial QoE", "0.91 confidence"],
  ["Director charge filing note", "Legal / Corporate", "Registry-linked"],
  ["GST notice summary", "Tax", "Needs follow-up"],
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
  "Document, evidence, request-list, and Q&A endpoints",
  "Source-adapter catalog shaped for India and vendor readiness",
];

const nextBridge = [
  "Move from metadata-only document intake to parsing and extraction.",
  "Populate issue flags and reviewer gates from normalized evidence.",
  "Start the first buy-side diligence vertical slice over the new persistence layer.",
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
          <h1>India due diligence, now operating on real case records.</h1>
          <p className={styles.lead}>
            Phase 2 converts the foundation into a true operating layer:
            persisted cases, document metadata, evidence records, request
            tracking, management Q&amp;A, and source-adapter contracts for
            India diligence.
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
          </div>

          <div className={styles.column}>
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
              <h2>Immediate Phase 3 bridge</h2>
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
