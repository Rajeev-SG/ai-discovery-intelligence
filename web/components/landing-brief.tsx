import Link from "next/link";
import { clampText, type BriefOutcome, type BriefItem } from "@/lib/intel";
import { formatDate } from "@/lib/evidence";
import { CONFIDENCE_LABELS, evidenceHref, type ConfidenceLabel } from "@/lib/pov";

/**
 * Weekly executive brief (issue #45). Renders the real `GET /brief` output:
 * the material change, why it matters, the agency action, confidence and
 * significance. A `state:"empty"` brief says "no material item qualifies this
 * week" — distinct from an unreachable backend, which says so plainly.
 *
 * Each card leads with the change, confidence and significance. The standing
 * "why it matters" / "agency action" framing is deterministic per event type
 * (`config/brief_copy.yaml`), so it repeats across items; it is disclosed behind
 * a per-card expander to keep the default view readable.
 */
function confidenceLabel(value: string): string {
  return CONFIDENCE_LABELS[value as ConfidenceLabel] ?? value;
}

function BriefCard({ item }: { item: BriefItem }) {
  return (
    <li className="brief-item" data-testid="brief-item">
      <div className="brief-item-head">
        <span className="pill brief-confidence">confidence: {confidenceLabel(item.confidence)}</span>
        <span className="pill brief-significance">significance {item.significance.toFixed(2)}</span>
        {item.is_watch_item ? <span className="pill brief-watch">watch item</span> : null}
        {item.surfaces.map((surface) => (
          <Link
            className="pill pill-surface"
            key={surface}
            href={`/surfaces?q=${encodeURIComponent(surface)}`}
          >
            {surface}
          </Link>
        ))}
      </div>
      <p className="brief-change">{clampText(item.change)}</p>
      <details className="brief-why-details">
        <summary>Why it matters &amp; what to do</summary>
        <dl className="brief-why">
          <div>
            <dt>Why it matters</dt>
            <dd>{clampText(item.why_it_matters)}</dd>
          </div>
          <div>
            <dt>Agency action</dt>
            <dd>{clampText(item.agency_action)}</dd>
          </div>
        </dl>
        {item.evidence_ids.length ? (
          <p className="brief-evidence">
            <Link href={evidenceHref(item.evidence_ids[0])}>Evidence →</Link>
          </p>
        ) : null}
      </details>
    </li>
  );
}

export function LandingBrief({ outcome }: { outcome: BriefOutcome }) {
  const brief = outcome.brief;
  return (
    <section className="landing-section" aria-labelledby="landing-brief-title" data-testid="landing-brief">
      <header className="landing-section-head">
        <div>
          <p className="eyebrow">Weekly executive brief</p>
          <h2 id="landing-brief-title">What matters this week</h2>
          {brief && outcome.status !== "error" ? (
            <p className="landing-lede" data-testid="brief-window">
              Window {formatDate(brief.window_start)} → {formatDate(brief.window_end)} · generated{" "}
              {formatDate(brief.generated_at)}
            </p>
          ) : null}
        </div>
      </header>

      {outcome.status === "error" || outcome.status === "unconfigured" ? (
        <p className="landing-state landing-state-error" data-testid="brief-unavailable">
          The weekly brief service is not reachable right now. No brief is shown rather than
          fabricating one.
        </p>
      ) : brief && brief.items.length ? (
        <ul className="brief-list" data-testid="brief-list">
          {brief.items.map((item, index) => (
            <BriefCard key={`${item.surfaces.join("-")}-${index}`} item={item} />
          ))}
        </ul>
      ) : (
        <p className="landing-state" data-testid="brief-empty">
          No material item qualifies this week. The deterministic gate adopted nothing above the
          significance threshold rather than padding the brief.
        </p>
      )}
    </section>
  );
}
