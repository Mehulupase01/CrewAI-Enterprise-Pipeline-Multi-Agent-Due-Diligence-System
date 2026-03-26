import styles from "./page.module.css";

const motionPacks = [
  "Buy-side M&A / PE due diligence",
  "Credit / lending expansion-ready",
  "Vendor / partner onboarding expansion-ready",
];

const sectorPacks = [
  "Tech / SaaS / Services live first",
  "Manufacturing / Industrials planned",
  "Fintech / NBFC / BFSI planned",
];

const foundationTracks = [
  "FastAPI control plane and pack contracts",
  "CrewAI orchestration runtime",
  "Evidence ledger and issue taxonomy",
  "Analyst workbench and reviewer flows",
];

const phaseGoals = [
  "Phase 0: architecture lock, pack model, verification gates",
  "Phase 1: backend, web, Docker stack, scripts, core tests",
  "Phase 2: evidence ingestion, OCR, normalization, provenance",
  "Phase 3: first India buy-side diligence vertical slice",
];

export default function Home() {
  return (
    <div className={styles.page}>
      <div className={styles.auraLeft} />
      <div className={styles.auraRight} />
      <main className={styles.main}>
        <section className={styles.hero}>
          <span className={styles.kicker}>CrewAI Enterprise Pipeline</span>
          <h1>India due diligence, built like an operating system.</h1>
          <p className={styles.lead}>
            The foundation is now shaped around structured evidence, pack-based
            workflows, reviewer approvals, and future-ready expansion for
            lending, onboarding, manufacturing, and BFSI.
          </p>
          <div className={styles.heroMeta}>
            <div>
              <span className={styles.metaLabel}>Live motion</span>
              <strong>Buy-side diligence</strong>
            </div>
            <div>
              <span className={styles.metaLabel}>Live sector</span>
              <strong>Tech / SaaS / Services</strong>
            </div>
            <div>
              <span className={styles.metaLabel}>Current build</span>
              <strong>Phase 0 / 1 foundation</strong>
            </div>
          </div>
        </section>

        <section className={styles.grid}>
          <article className={styles.panel}>
            <div className={styles.panelHeader}>
              <span className={styles.badge}>Motion packs</span>
              <h2>Current and planned workflow surfaces</h2>
            </div>
            <ul className={styles.list}>
              {motionPacks.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </article>

          <article className={styles.panel}>
            <div className={styles.panelHeader}>
              <span className={styles.badge}>Sector packs</span>
              <h2>Expansion model without core rewrites</h2>
            </div>
            <ul className={styles.list}>
              {sectorPacks.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </article>

          <article className={styles.panel}>
            <div className={styles.panelHeader}>
              <span className={styles.badge}>Foundation tracks</span>
              <h2>What the current implementation pass is laying down</h2>
            </div>
            <ul className={styles.list}>
              {foundationTracks.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </article>

          <article className={styles.panel}>
            <div className={styles.panelHeader}>
              <span className={styles.badge}>Phase gates</span>
              <h2>How we keep the project verifiable</h2>
            </div>
            <ul className={styles.list}>
              {phaseGoals.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </article>
        </section>
      </main>
    </div>
  );
}
