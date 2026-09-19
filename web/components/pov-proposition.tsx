import {
  CONFIDENCE_LABELS,
  evidenceHref,
  formatDate,
  isContested,
  isUnresolved,
  type PovEvidence,
  type PovProposition as PovPropositionModel,
} from "@/lib/pov";

function EvidenceList({ items, kind }: { items: PovEvidence[]; kind: "supporting" | "contradicting" }) {
  if (!items.length) {
    return <p className="pov-empty">No {kind} evidence recorded.</p>;
  }
  return (
    <ul className={`pov-evidence pov-evidence-${kind}`}>
      {items.map((bullet) => (
        <li key={bullet.claim_id || `${bullet.slot}-${bullet.text}`}>
          <span className="pov-evidence-text">{bullet.text}</span>
          <span className="pov-evidence-meta">
            {bullet.value_text ? <span className="pill">{bullet.value_text}</span> : null}
            <span className={`pill pov-conf-${bullet.confidence}`}>
              {CONFIDENCE_LABELS[bullet.confidence]}
            </span>
            <span className="pov-evidence-date">effective {formatDate(bullet.effective_at)}</span>
            {bullet.claim_id ? (
              <a href={evidenceHref(bullet.claim_id)}>evidence {bullet.claim_id.slice(0, 12)}</a>
            ) : null}
          </span>
        </li>
      ))}
    </ul>
  );
}

export function PovProposition({ proposition }: { proposition: PovPropositionModel }) {
  const unresolved = isUnresolved(proposition);
  const contested = isContested(proposition);
  const evidenceCount = proposition.supporting.length + proposition.contradicting.length;
  return (
    <section className="pov-prop" id={proposition.id} aria-labelledby={`${proposition.id}-title`}>
      <header className="pov-prop-head">
        <div>
          <p className="pov-prop-section">{proposition.section}</p>
          <h2 id={`${proposition.id}-title`}>{proposition.id}</h2>
        </div>
        <div className="pov-prop-badges">
          <span className={`pill pov-conf-${proposition.confidence}`}>
            confidence: {CONFIDENCE_LABELS[proposition.confidence]}
          </span>
          {contested ? <span className="pill pov-contested">contested</span> : null}
          {unresolved ? <span className="pill pov-unresolved">unresolved</span> : null}
        </div>
      </header>

      <p className="pov-prop-base">{proposition.base_text}</p>

      <p className="pov-prop-meta">
        Last reviewed: {formatDate(proposition.last_reviewed)}
        {unresolved ? " · no evidence has cleared the gate yet" : ""}
      </p>

      <dl className="pov-prop-counts">
        <div>
          <dt>Supporting</dt>
          <dd>{proposition.supporting.length}</dd>
        </div>
        <div>
          <dt>Contradicting</dt>
          <dd>{proposition.contradicting.length}</dd>
        </div>
      </dl>

      {contested ? (
        <div className="pov-contradiction" role="note">
          Live contradicting evidence caps this position at low confidence.
        </div>
      ) : null}

      {evidenceCount > 0 ? (
        <details className="pov-evidence-details">
          <summary>Evidence detail ({evidenceCount})</summary>
          <div className="pov-evidence-body">
            <h3>Supporting</h3>
            <EvidenceList items={proposition.supporting} kind="supporting" />
            <h3>Contradicting</h3>
            <EvidenceList items={proposition.contradicting} kind="contradicting" />
            <p className="pov-topics">
              Topics: {proposition.topics.map((t) => <span className="pill" key={t}>{t}</span>)}
            </p>
          </div>
        </details>
      ) : (
        <p className="pov-empty">
          No supporting or contradicting evidence yet — the base position stands alone.
        </p>
      )}
    </section>
  );
}
