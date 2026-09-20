/**
 * Presentational rendering of one resolved reconciliation relationship (issue
 * #47). Every decision shown here — state, relationship, confidence adjustment,
 * differences, interpretation — is copied verbatim from the persisted ledger.
 * The component only lays it out and links back into evidence detail.
 */
import {
  dimensionLabel,
  formatAdjustment,
  formatValue,
  relationshipLabel,
  stateLabel,
  surfaceHref,
  type ResolvedRelationship,
  type ResolvedSide,
} from "@/lib/reconciliation";

function SideValue({ side }: { side: ResolvedSide }) {
  const { claim, metric } = side;
  if (!claim) {
    // Distinguish "the ledger could not be read" from "this claim is absent":
    // claiming a referenced claim does not exist when the fetch simply failed
    // would be misleading.
    return (
      <div className="recon-side recon-side-missing">
        <p className="recon-side-missing-note" data-testid="recon-side-ledger-state">
          {side.ledgerUnavailable ? (
            <>
              Claim ledger unreachable — <code>{side.ref.claim_id}</code> could not be resolved.
            </>
          ) : (
            <>
              Referenced claim <code>{side.ref.claim_id}</code> is not in the claim ledger.
            </>
          )}
        </p>
      </div>
    );
  }
  return (
    <div className={`recon-side${side.superseded ? " recon-side-superseded" : ""}`}>
      <div className="recon-side-head">
        <h3 className="recon-side-statement">{claim.statement}</h3>
        {side.superseded && <span className="recon-badge recon-badge-superseded">Superseded — still inspectable</span>}
      </div>
      <dl className="recon-side-values">
        {claim.value.map((value) => (
          <div key={value.metric_id} className="recon-value-row">
            <dt>{value.label || value.metric_id}</dt>
            <dd>
              <span className={value.known ? "recon-value" : "recon-value recon-value-unknown"}>
                {formatValue(value)}
              </span>
              {value.window && <span className="recon-value-window"> · {value.window}</span>}
              {value.scope && <span className="recon-value-scope"> · {value.scope}</span>}
            </dd>
          </div>
        ))}
      </dl>
      {metric && (
        <p className="recon-side-ref">
          Compared metric: <code>{metric.metric_id}</code> — {metric.label}
        </p>
      )}
      <p className="recon-side-meta">
        {claim.source?.publisher && <span>{claim.source.publisher}</span>}
        {claim.source?.url && (
          <a href={claim.source.url} target="_blank" rel="noreferrer">
            source
          </a>
        )}
        {claim.topic && <span className="recon-side-topic">{claim.topic.replace(/_/g, " ")}</span>}
        {side.surface && (
          <a href={surfaceHref(side.surface)} data-testid={`recon-link-${side.surface}`}>
            evidence for {side.surface}
          </a>
        )}
      </p>
    </div>
  );
}

function ContextDetail({ relationship }: { relationship: ResolvedRelationship }) {
  const { item } = relationship;
  return (
    <details className="recon-context" data-testid="recon-context">
      <summary>Comparison context and methodology</summary>
      <div className="recon-context-body">
        <div className="recon-context-block">
          <h4>Differences that explain the relationship</h4>
          {item.differences.length > 0 ? (
            <ul className="recon-chips" data-testid="recon-differences">
              {item.differences.map((d) => (
                <li key={d} className="recon-chip recon-chip-diff">
                  {dimensionLabel(d)}
                </li>
              ))}
            </ul>
          ) : (
            <p className="recon-empty">No dimension difference recorded.</p>
          )}
        </div>
        <div className="recon-context-block">
          <h4>Unknown context dimensions</h4>
          {item.unknown_dimensions.length > 0 ? (
            <ul className="recon-chips" data-testid="recon-unknowns">
              {item.unknown_dimensions.map((d) => (
                <li key={d} className="recon-chip recon-chip-unknown">
                  {dimensionLabel(d)}
                </li>
              ))}
            </ul>
          ) : (
            <p className="recon-empty">No unknown dimensions — context is complete.</p>
          )}
        </div>
      </div>
    </details>
  );
}

export function ReconciliationRelationship({ relationship }: { relationship: ResolvedRelationship }) {
  const { item, sides } = relationship;
  return (
    <article
      className={`recon-rel recon-rel-${relationship.category}${relationship.contested ? " recon-rel-contested" : ""}`}
      data-testid="recon-rel"
      data-state={item.state}
      data-relationship={item.relationship}
    >
      <header className="recon-rel-head">
        <div className="recon-rel-badges">
          <span className="recon-badge recon-badge-relationship">{relationshipLabel(item.relationship)}</span>
          <span className="recon-badge recon-badge-state">{stateLabel(item.state)}</span>
          {relationship.contested && <span className="recon-badge recon-badge-contested">Contested</span>}
        </div>
        <p className="recon-adjustment">
          Confidence adjustment <strong data-testid="recon-adjustment">{formatAdjustment(item.confidence_adjustment)}</strong>
        </p>
      </header>

      <div className="recon-sides">
        {sides.map((side) => (
          <SideValue key={side.ref.raw} side={side} />
        ))}
      </div>

      <blockquote className="recon-interpretation" data-testid="recon-interpretation">
        <span className="recon-interpretation-label">Agency interpretation</span>
        {item.interpretation}
      </blockquote>

      <ContextDetail relationship={relationship} />
    </article>
  );
}
