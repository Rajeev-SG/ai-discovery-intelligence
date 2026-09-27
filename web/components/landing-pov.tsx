import Link from "next/link";
import {
  CONFIDENCE_LABELS,
  formatDate,
  hasChanges,
  isContested,
  isUnresolved,
  type PovView,
} from "@/lib/pov";
import { PovChangelog } from "@/components/pov-changelog";

/**
 * Current POV (issue #45). A concise projection of the canonical POV artifact —
 * proposition state, confidence and contested flag rendered verbatim through
 * `@/lib/pov` (no re-derivation) and the most recent adopted change. The full
 * evidence and change history live at `/pov`; this block links there.
 */
/**
 * Current POV (issue #45). A concise projection of the canonical POV artifact —
 * proposition state, confidence and contested flag rendered verbatim through
 * `@/lib/pov` (no re-derivation) and the most recent adopted change. The full
 * evidence and change history live at `/pov`; this block links there.
 *
 * Issue #69: internal source paths and version metadata are removed from the
 * reading layer; proposition links read as human summaries, not raw ids.
 */
export function LandingPov({ view }: { view: PovView }) {
  const changed = hasChanges(view);
  const recent = changed ? [...view.changelog].slice(-1) : [];
  return (
    <section className="landing-section" aria-labelledby="landing-pov-title" data-testid="landing-pov">
      <header className="landing-section-head">
        <div>
          <p className="eyebrow">Current POV</p>
          <h2 id="landing-pov-title">What we currently believe</h2>
          <p className="landing-lede">
            {changed ? `${view.changelog.length} change${view.changelog.length === 1 ? "" : "s"} recorded` : "No POV change recorded yet."}
          </p>
        </div>
        <Link className="landing-link" href="/pov" data-testid="landing-pov-more">
          Full POV and changelog →
        </Link>
      </header>

      <ul className="pov-summary" data-testid="pov-summary">
        {view.propositions.map((proposition) => {
          const unresolved = isUnresolved(proposition);
          const contested = isContested(proposition);
          return (
            <li className="pov-summary-item" key={proposition.id}>
              <div className="pov-summary-head">
                <Link
                  className="pov-summary-id"
                  href={`/pov#${proposition.id}`}
                  title={proposition.id}
                >
                  {proposition.section || proposition.id}
                </Link>
                <span className={`pill pov-conf-${proposition.confidence}`}>
                  confidence: {CONFIDENCE_LABELS[proposition.confidence]}
                </span>
                {contested ? <span className="pill pov-contested">contested</span> : null}
                {unresolved ? <span className="pill pov-unresolved">unresolved</span> : null}
              </div>
              <p className="pov-summary-base">{proposition.base_text}</p>
              <p className="pov-summary-meta">
                Last reviewed {formatDate(proposition.last_reviewed)} ·{" "}
                {proposition.supporting.length} supporting · {proposition.contradicting.length} contradicting
              </p>
            </li>
          );
        })}
      </ul>

      <div className="pov-recent">
        <h3>Recent POV change</h3>
        {recent.length ? (
          <PovChangelog
            revisions={recent}
            labels={Object.fromEntries(view.propositions.map((p) => [p.id, p.section || p.id]))}
          />
        ) : (
          <p className="pov-empty" role="status">
            No POV change has been adopted — the gate adopted nothing rather than fabricating churn.
          </p>
        )}
      </div>
    </section>
  );
}
