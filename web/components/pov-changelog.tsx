import {
  CONFIDENCE_LABELS,
  evidenceHref,
  formatDateTime,
  type ConfidenceLabel,
  type PovRevision,
} from "@/lib/pov";

/**
 * The POV change history, chronological (oldest first — the projection sorts it).
 * An empty changelog is a valid, visible outcome: "no POV change".
 *
 * Issue #69: the proposition link always targets `/pov#<id>` — a bare `#id`
 * here silently targeted the *current* page (on the homepage it matched
 * nothing). Reading-layer copy shows human labels and links; raw event ids and
 * significance stay in the technical details.
 */
export function PovChangelog({ revisions }: { revisions: PovRevision[] }) {
  if (!revisions.length) {
    return (
      <p className="pov-empty" role="status">
        No POV change has been adopted. An event that fails the deterministic gate
        leaves the propositions above untouched — no churn is fabricated.
      </p>
    );
  }
  return (
    <ol className="pov-changelog">
      {revisions.map((revision) => (
        <li className="pov-change" key={`${revision.proposition_id}-${revision.changed_at}-${revision.event_id}`}>
          <header className="pov-change-head">
            <a className="pov-change-prop" href={`/pov#${revision.proposition_id}`}>
              {revision.proposition_id}
            </a>
            <span className="pov-change-date">{formatDateTime(revision.changed_at)}</span>
          </header>
          <p className="pov-change-reason">{revision.reason}</p>
          <p className="pov-change-meta">
            <span className={`pill pov-conf-${revision.confidence}`}>
              confidence: {CONFIDENCE_LABELS[revision.confidence as ConfidenceLabel] ?? revision.confidence}
            </span>
          </p>
          <details className="pov-change-statement">
            <summary>Before → after &amp; method</summary>
            <p className="pov-change-method">
              {revision.evidence_ids.length
                ? `${revision.evidence_ids.length} supporting observation${revision.evidence_ids.length === 1 ? "" : "s"}.`
                : null}{" "}
              Significance {revision.significance.toFixed(2)}.
            </p>
            <div className="pov-diff">
              <div>
                <h3>Before</h3>
                <pre>{revision.old_statement}</pre>
              </div>
              <div>
                <h3>After</h3>
                <pre>{revision.new_statement}</pre>
              </div>
            </div>
          </details>
          {revision.evidence_ids.length ? (
            <p className="pov-change-evidence">
              <a href={evidenceHref(revision.evidence_ids[0])}>See the evidence →</a>
            </p>
          ) : null}
        </li>
      ))}
    </ol>
  );
}
