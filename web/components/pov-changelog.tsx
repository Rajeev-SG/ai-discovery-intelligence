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
            <a className="pov-change-prop" href={`#${revision.proposition_id}`}>
              {revision.proposition_id}
            </a>
            <span className="pov-change-date">{formatDateTime(revision.changed_at)}</span>
          </header>
          <p className="pov-change-reason">{revision.reason}</p>
          <p className="pov-change-meta">
            <span className="pill">significance {revision.significance.toFixed(2)}</span>
            <span className={`pill pov-conf-${revision.confidence}`}>
              confidence: {CONFIDENCE_LABELS[revision.confidence as ConfidenceLabel] ?? revision.confidence}
            </span>
            {revision.event_id ? <span className="pov-change-event">event {revision.event_id}</span> : null}
          </p>
          <details className="pov-change-statement">
            <summary>Before → after</summary>
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
              Evidence:{" "}
              {revision.evidence_ids.map((id) => (
                <a key={id} href={evidenceHref(id)}>
                  {id.slice(0, 12)}
                </a>
              ))}
            </p>
          ) : null}
        </li>
      ))}
    </ol>
  );
}
