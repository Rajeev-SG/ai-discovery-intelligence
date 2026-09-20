"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { loadSurfaceMechanics } from "@/lib/mechanics-actions";
import {
  MECHANICS_STATE_LABELS,
  evidenceClassLabel,
  type MechanicsAssertion,
  type MechanicsDimension,
  type MechanicsEvidence,
  type ReconciliationRecord,
  type SurfaceMechanics,
  type SurfaceMechanicsOutcome,
} from "@/lib/mechanics";

/**
 * Marketer-facing evidence & trust layer (Phase 2, issue #58).
 *
 * Renders the backend mechanics projection with simple evidence classes
 * (vendor-documented / independently researched / directly observed), and for
 * every evidenced dimension shows publisher, public URL, class, dates,
 * confidence with a one-line "why", methodology context, freshness and any
 * inline conflict. All values come from the backend; this module derives
 * nothing — it only labels, groups and links. Conflicts reuse the persisted
 * reconciliation records the backend joined in; the component never
 * re-implements reconciliation.
 */

const EVIDENCE_CLASS_ORDER = [
  "official_documentation",
  "controlled_observation",
  "independent_research",
] as const;

const STATE_ORDER: Record<string, number> = {
  conflicting: 0,
  partially_known: 1,
  known: 2,
  unknown: 3,
};

function classTone(value: string): string {
  if (value === "official_documentation") return "tone-official";
  if (value === "controlled_observation") return "tone-observed";
  return "tone-independent";
}

function formatDay(iso: string | null | undefined): string {
  return iso ? iso.slice(0, 10) : "date unknown";
}

/** The single best "why this confidence" line, or an honest absence. */
function whyConfidence(evidence: MechanicsEvidence): string {
  const first = evidence.confidence_rationale?.[0];
  if (first) return first;
  return "The backend recorded no rationale for this confidence.";
}

function EvidenceTrust({ evidence }: { evidence: MechanicsEvidence }) {
  return (
    <li className={`trust-evidence ${classTone(evidence.evidence_class)}`} data-testid="trust-evidence">
      <div className="trust-evidence-head">
        <span className={`chip chip-class ${classTone(evidence.evidence_class)}`}>
          {evidenceClassLabel(evidence.evidence_class)}
        </span>
        <span className={`chip chip-confidence confidence-${evidence.confidence}`}>
          {evidence.confidence} confidence
        </span>
        {evidence.freshness_state ? (
          <span className="chip chip-freshness">
            {evidence.freshness_state === "unknown"
              ? "freshness unknown"
              : `${evidence.freshness_state}${evidence.freshness_age_days != null ? ` · ${evidence.freshness_age_days}d` : ""}`}
          </span>
        ) : null}
      </div>

      <dl className="trust-evidence-grid">
        <div>
          <dt>Publisher</dt>
          <dd>{evidence.publisher ?? "Unknown"}</dd>
        </div>
        <div>
          <dt>Evidence class</dt>
          <dd>{evidenceClassLabel(evidence.evidence_class)}</dd>
        </div>
        <div>
          <dt>Date</dt>
          <dd>
            {evidence.published_at ? `published ${formatDay(evidence.published_at)}` : null}
            {evidence.observed_at ? ` · observed ${formatDay(evidence.observed_at)}` : null}
            {!evidence.published_at && !evidence.observed_at ? "date unknown" : null}
          </dd>
        </div>
        <div>
          <dt>Public source</dt>
          <dd>
            {evidence.url ? (
              <a href={evidence.url} target="_blank" rel="noreferrer noopener">
                {evidence.url}
              </a>
            ) : (
              "No public URL"
            )}
          </dd>
        </div>
      </dl>

      <p className="trust-why" data-testid="trust-why">
        <strong>Why this confidence:</strong> {whyConfidence(evidence)}
      </p>

      {/* When the rationale had to be re-derived from the persisted evidence, state
          the label it actually supports. If that differs from the stored label the
          claim carries, say so explicitly rather than implying agreement (issue
          #58 review DELTA-1). */}
      {evidence.derived_label && evidence.derived_label !== evidence.confidence ? (
        <p className="trust-derived-note" data-testid="trust-derived-note">
          This rationale was re-derived from the stored evidence and supports{" "}
          <strong>{evidence.derived_label}</strong> confidence, while the claim is
          recorded as <strong>{evidence.confidence}</strong>.{" "}
          {evidence.derived_label === "high" ? "The stored label is the more cautious reading." : null}
        </p>
      ) : null}

      {(evidence.methodology_notes || evidence.measurement_mode || (evidence.methodology_completeness ?? "") !== "") ? (
        <p className="trust-methodology">
          <strong>Methodology:</strong>{" "}
          {evidence.methodology_notes
            ? evidence.methodology_notes
            : evidence.measurement_mode
              ? `Measurement mode: ${evidence.measurement_mode}.`
              : "No methodology context published."}
          {evidence.methodology_completeness && evidence.methodology_completeness !== "not_stated"
            ? ` (${evidence.methodology_completeness})`
            : null}
        </p>
      ) : null}

      {evidence.limitations?.length ? (
        <p className="trust-limitations">
          <strong>Limitations:</strong> {evidence.limitations.join(" ")}
        </p>
      ) : null}

      {evidence.modes?.length || evidence.regions?.length ? (
        <p className="trust-scope">
          {evidence.modes?.length ? <>Mode: {evidence.modes.join(", ")}. </> : null}
          {evidence.regions?.length ? <>Region: {evidence.regions.join(", ")}. </> : null}
        </p>
      ) : null}

      {evidence.reconciliation?.length ? (
        <ul className="trust-conflicts" data-testid="trust-conflicts">
          {evidence.reconciliation.map((rec, i) => (
            <ConflictNote key={`${rec.state}-${i}`} record={rec} />
          ))}
        </ul>
      ) : null}

      <details className="trust-technical">
        <summary>Technical record</summary>
        <p className="trust-technical-line">
          Claim <code>{evidence.claim_id}</code>
          {evidence.source_class ? <> · source class <code>{evidence.source_class}</code></> : null}
          {evidence.confidence_score != null ? <> · score {evidence.confidence_score}</> : null}
          {evidence.relates_to_claim_id ? <> · relates to <code>{evidence.relates_to_claim_id}</code></> : null}
        </p>
      </details>
    </li>
  );
}

/**
 * An inline conflict. The interpretation, state and relationship are the
 * backend's own reconciliation output — this only presents them and links to the
 * full reconciliation view. Nothing is re-derived here.
 */
function ConflictNote({ record }: { record: ReconciliationRecord }) {
  return (
    <li className="trust-conflict" data-testid="trust-conflict">
      <span className="chip chip-conflict">{record.state.replace(/_/g, " ")}</span>
      <p className="trust-conflict-text">{record.interpretation}</p>
      {record.differences?.length ? (
        <p className="muted">Differs on: {record.differences.join(", ")}</p>
      ) : null}
      <Link className="trust-conflict-link" href="/reconciliation">
        Compare the contradicting evidence →
      </Link>
    </li>
  );
}

function DimensionTrust({ dimension }: { dimension: MechanicsDimension }) {
  const isUnknown = dimension.state === "unknown";
  return (
    <article
      className={`trust-dimension state-${dimension.state}`}
      data-testid={`trust-dimension-${dimension.dimension}`}
    >
      <header className="trust-dimension-head">
        <h3>{dimension.label}</h3>
        <span className={`chip state-${dimension.state}`}>{MECHANICS_STATE_LABELS[dimension.state]}</span>
      </header>
      <p className="trust-definition">{dimension.definition}</p>
      {isUnknown ? (
        <p className="detail-empty" data-testid="trust-unknown">
          {dimension.note || "No validated evidence yet — unknown is a valid answer."}
        </p>
      ) : (
        dimension.assertions.map((assertion, ai) => (
          <div className="trust-assertion" key={ai}>
            <p className="trust-statement">{assertion.statement}</p>
            {assertion.conflict_note ? <p className="trust-conflict-note">{assertion.conflict_note}</p> : null}
            <ul className="trust-evidence-list">
              {assertion.evidence.map((ev) => (
                <EvidenceTrust key={ev.claim_id} evidence={ev} />
              ))}
            </ul>
          </div>
        ))
      )}
    </article>
  );
}

export function MechanicsTrust({ surface }: { surface: SurfaceMechanics }) {
  const evidenced = surface.dimensions.filter((d) => d.state !== "unknown");
  const unknown = surface.dimensions.filter((d) => d.state === "unknown");
  const ordered = [...evidenced].sort(
    (a, b) => (STATE_ORDER[a.state] ?? 9) - (STATE_ORDER[b.state] ?? 9),
  );

  return (
    <div className="trust">
      <p className="trust-summary" data-testid="trust-summary">
        <strong>{surface.evidenced_dimension_count}</strong> of {surface.dimension_count} mechanics
        dimensions are evidenced for this surface.{" "}
        {unknown.length
          ? `${unknown.length} remain explicitly unknown — unknown is a valid answer, not a missing value.`
          : "Every dimension carries evidence."}
      </p>

      {ordered.length ? (
        <div className="trust-dimensions">
          {ordered.map((dimension) => (
            <DimensionTrust key={dimension.dimension} dimension={dimension} />
          ))}
        </div>
      ) : (
        <p className="detail-empty" data-testid="trust-none">
          No mechanics dimension is evidenced yet. The product shows this honestly rather than
          inferring behaviour from the registry.
        </p>
      )}

      {unknown.length ? (
        <details className="trust-unknown-list">
          <summary>{unknown.length} dimensions with no evidence yet</summary>
          <ul>
            {unknown.map((d) => (
              <li key={d.dimension}>
                <strong>{d.label}</strong> — {d.note}
              </li>
            ))}
          </ul>
        </details>
      ) : null}
    </div>
  );
}

export { EVIDENCE_CLASS_ORDER };

/**
 * Lazy wrapper: fetches one surface's mechanics projection on mount (client) via
 * the server action, then renders the trust layer. Keeps the drawer's above-the-
 * fold content light and reports an explicit failed/unconfigured state — an
 * unreachable backend is never shown as "no mechanics".
 */
export function MechanicsTrustPanel({ surfaceId }: { surfaceId: string }) {
  const [outcome, setOutcome] = useState<SurfaceMechanicsOutcome | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    let active = true;
    loadSurfaceMechanics(surfaceId)
      .then((result) => {
        if (active) setOutcome(result);
      })
      .catch(() => {
        if (active) setError(true);
      });
    return () => {
      active = false;
    };
  }, [surfaceId]);

  if (error) {
    return (
      <p className="detail-empty" data-testid="trust-error">
        Evidence &amp; trust could not be loaded. No mechanics are invented.
      </p>
    );
  }
  if (!outcome) {
    return (
      <p className="detail-empty" data-testid="trust-loading">
        Loading evidenced mechanics…
      </p>
    );
  }
  if (outcome.status === "unconfigured" || outcome.status === "error") {
    return (
      <p className="detail-hint" data-testid="trust-unavailable">
        The evidenced-mechanics source is unavailable right now (
        {outcome.status === "unconfigured" ? "not configured" : "request failed"}). The mechanics
        state is unknown, not confirmed empty.
      </p>
    );
  }
  if (outcome.status === "unknown_surface" || !outcome.surface) {
    return (
      <p className="detail-empty" data-testid="trust-unknown-surface">
        This surface is not in the canonical registry, so there is no mechanics projection.
      </p>
    );
  }
  return <MechanicsTrust surface={outcome.surface} />;
}
