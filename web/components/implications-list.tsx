/**
 * Marketing implications view (Phase 2, issue #59).
 *
 * Renders the backend's evidence-backed implications. Every card shows the
 * restrained action, why it follows (rationale), the evidence it rests on, the
 * surfaces/regions it applies to, and — kept distinct — its confidence and its
 * actionability. Evidence-free or non-actionable surfaces render an explicit
 * "monitor, no action" state. Nothing is derived in React.
 */
import Link from "next/link";
import {
  actionabilityLabel,
  familyLabel,
  type Implication,
  type ImplicationsProjection,
} from "@/lib/implications";

function ClaimRefs({ ids, label }: { ids: string[]; label: string }) {
  if (!ids.length) return null;
  return (
    <p className="impl-evidence-line">
      <span className="impl-evidence-label">{label}:</span>{" "}
      {ids.map((id) => (
        <code key={id}>{id.slice(0, 10)}</code>
      ))}
    </p>
  );
}

function ImplicationCard({ impl, showSurfaces = true }: { impl: Implication; showSurfaces?: boolean }) {
  return (
    <article className={`impl-card family-${impl.family}`} data-testid="impl-card">
      <header className="impl-card-head">
        <span className="chip impl-family">{familyLabel(impl.family)}</span>
        <span className={`chip impl-actionability actionability-${impl.actionability}`}>
          {actionabilityLabel(impl.actionability)}
        </span>
        <span className={`chip chip-confidence confidence-${impl.confidence}`}>
          {impl.confidence} confidence
        </span>
      </header>

      <p className="impl-action">{impl.action}</p>
      <p className="impl-rationale">
        <strong>Why:</strong> {impl.rationale}
      </p>

      {showSurfaces && impl.surfaces.length ? (
        <p className="impl-scope">
          <strong>Applies to:</strong>{" "}
          {impl.surfaces.map((s) => (
            <Link key={s} className="impl-surface-link" href={`/surfaces?surface=${encodeURIComponent(s)}`}>
              {s}
            </Link>
          ))}
          {impl.regions.length ? <> · region {impl.regions.join(", ")}</> : null}
          {impl.modes.length ? <> · mode {impl.modes.join(", ")}</> : null}
        </p>
      ) : null}

      <ClaimRefs ids={impl.supporting_claim_ids} label="Supported by" />
      {impl.contradicting_claim_ids.length ? (
        <ClaimRefs ids={impl.contradicting_claim_ids} label="Contradicted by" />
      ) : null}

      <details className="impl-technical">
        <summary>Significance &amp; method</summary>
        <p className="impl-technical-line">
          Significance {impl.significance.toFixed(2)} (reuses the POV significance
          machinery). Confidence and actionability are separate axes: confidence is
          how strong the evidence is, actionability is how much you can change.
          {impl.supporting_dimensions.length ? (
            <>
              {" "}
              Dimensions: {impl.supporting_dimensions.join(", ")}.
            </>
          ) : null}
        </p>
      </details>

      {impl.note ? <p className="impl-note">{impl.note}</p> : null}
    </article>
  );
}

export function ImplicationsList({ projection }: { projection: ImplicationsProjection }) {
  const cross = projection.cross_surface;
  const actionable = cross.filter((i) => !i.monitor_only);
  // Monitor surfaces come from the per-surface payload, independent of the
  // actionable count, so an all-monitor-only ledger still shows them (impl-004).
  const monitorSurfaces = Object.values(projection.surfaces).filter((s) => s.monitor_only);

  return (
    <div className="impl-list">
      <section className="impl-section">
        <h2>What to do, and why</h2>
        <p className="impl-intro">
          {actionable.length} evidence-backed implication{actionable.length === 1 ? "" : "s"} across{" "}
          {new Set(actionable.flatMap((i) => i.surfaces)).size} surface
          {new Set(actionable.flatMap((i) => i.surfaces)).size === 1 ? "" : "s"}. Every
          action cites the validated claims it rests on. Where evidence is
          insufficient, the product says so rather than inventing advice.
        </p>
        {actionable.length ? (
          <div className="impl-cards" data-testid="impl-cards">
            {actionable.map((impl, index) => (
              <ImplicationCard key={`${impl.family}-${index}`} impl={impl} />
            ))}
          </div>
        ) : (
          <p className="impl-empty" data-testid="impl-none">
            No surfaced mechanic is actionable yet. Nothing is recommended rather than
            offering generic advice.
          </p>
        )}
      </section>

      {monitorSurfaces.length ? (
        <section className="impl-section impl-monitor">
          <h2>Monitor only</h2>
          <p className="impl-intro">
            These surfaces have no evidenced, actionable mechanic. The correct action is
            to watch, not to act on assumption.
          </p>
          <ul className="impl-monitor-list" data-testid="impl-monitor-list">
            {monitorSurfaces.map((s) => (
              <li key={s.surface}>
                <strong>{s.surface}</strong> — {s.note}
              </li>
            ))}
          </ul>
        </section>
      ) : null}
    </div>
  );
}

export { ImplicationCard };
