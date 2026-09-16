import Link from "next/link";
import { evidenceDate, loadEvidenceFeed } from "@/lib/evidence";
import styles from "./page.module.css";

export const dynamic = "force-dynamic";

export default async function EvidencePage() {
  const feed = await loadEvidenceFeed();
  return <main className={styles.main}>
    <nav aria-label="Product views"><Link href="/">← Observation plane</Link></nav>
    <header className={styles.header}>
      <p className={styles.eyebrow}>AI Discovery Intelligence · Source ledger</p>
      <h1>Evidence, before interpretation.</h1>
      <p>Public sources captured with dates, publisher context and a content fingerprint.
        Vendor research describes its own dataset—not a universal truth.</p>
    </header>
    {feed.status === "unavailable" ? <section role="status" className={styles.notice}>
      <h2>Evidence service unavailable</h2><p>{feed.message}</p>
      <p>The surface registry remains available. No fabricated or cached demo records are shown.</p>
    </section> : <>
      <p className={styles.summary}>{feed.items.length} shown · {feed.total} captured records ·
        Raw source snapshots remain private</p>
      {feed.items.length === 0 ? <p role="status">No sources have been captured yet. This does not mean no evidence exists.</p> :
        <ol className={styles.feed}>{feed.items.map(item => <li key={item.id} id={item.id}>
          <article>
            <div className={styles.context}>
              <span>{item.source_class.replaceAll("_", " ")}</span>
              <span>{item.publisher ?? "Publisher unknown"}</span>
              <span>{item.is_candidate ? "Discovery candidate · not canonical" : item.validation_status}</span>
            </div>
            <h2><a href={item.url} target="_blank" rel="noopener noreferrer">{item.title} ↗</a></h2>
            <dl className={styles.dates}>
              <div><dt>Published</dt><dd>{evidenceDate(item.published_at)}</dd></div>
              <div><dt>Updated by source</dt><dd>{evidenceDate(item.modified_at)}</dd></div>
              <div><dt>Captured (UTC)</dt><dd>{evidenceDate(item.observed_at)}</dd></div>
            </dl>
            <p className={styles.topics}>Topics: {item.topics.join(" · ") || "Not classified"}</p>
            <details><summary>Capture details and short excerpt</summary>
              {item.excerpt && <blockquote>{item.excerpt}</blockquote>}
              <dl><dt>Evidence ID</dt><dd><code>{item.id}</code></dd>
                <dt>Capture SHA-256</dt><dd><code>{item.capture_hash}</code></dd>
                <dt>Original source</dt><dd><a href={item.url}>{item.url}</a></dd></dl>
              <p>A capture is source evidence, not an automatically verified claim. Study methodology belongs with each extracted claim.</p>
            </details>
          </article>
        </li>)}</ol>}
      {feed.total > feed.items.length && <p>Showing the latest 100 records. The complete ledger remains in the evidence service.</p>}
    </>}
  </main>;
}
