"use client";

import { useEffect, useState } from "react";
import {
  buildHistory,
  formatDate,
  humaniseFreshness,
  isUnknownValue,
  leadingClaim,
  valueDisplay,
  type EvidenceClaim,
  type EvidenceValue,
  type HistoryStatus,
  type SurfaceDetail,
  type SurfaceEvidence,
} from "@/lib/evidence";
import { loadSurfaceDetail } from "@/lib/evidence-actions";

/** Public source link — new tab, no referrer, never a private capture path. */
function SourceLink({ url, label }: { url: string | null | undefined; label?: string }) {
  if (!url) return <span className="muted">No public source URL</span>;
  return (
    <a href={url} target="_blank" rel="noreferrer noopener">
      {label ?? url}
    </a>
  );
}

function Meta({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div>
      <dt>{label}</dt>
      <dd>{value}</dd>
    </div>
  );
}

function ValueRow({ value }: { value: EvidenceValue }) {
  const unknown = isUnknownValue(value);
  return (
    <li className={unknown ? "evidence-value evidence-value-unknown" : "evidence-value"} data-testid="evidence-value">
      <div className="evidence-value-head">
        <span className="evidence-value-label">{value.label || value.metric_id}</span>
        <span className={unknown ? "evidence-value-num is-unknown" : "evidence-value-num"}>
          {valueDisplay(value)}
          {value.unit ? <span className="evidence-value-unit"> {value.unit}</span> : null}
        </span>
      </div>
      <p className="evidence-value-meta">
        {value.window ? <span>Window: {value.window}</span> : <span>Window: unknown</span>}
        {" · "}
        {value.scope ? <span>Scope: {value.scope}</span> : <span>Scope: unknown</span>}
        {unknown ? " · Explicitly unknown" : null}
      </p>
    </li>
  );
}

function ClaimCard({ claim, index }: { claim: EvidenceClaim; index: number }) {
  const detail = claim.confidence_detail;
  const rationale = detail?.rationale ?? [];
  const inputs = Object.entries(detail?.inputs ?? {});
  return (
    <li className="evidence-claim" data-testid={`claim-${claim.claim_id}`}>
      <header className="evidence-claim-head">
        <span className="evidence-claim-index">Claim {index + 1}</span>
        <span className="chip">{claim.topic}</span>
        {claim.confidence ? (
          <span className={`chip chip-confidence confidence-${claim.confidence}`}>{claim.confidence} confidence</span>
        ) : null}
      </header>

      <p className="evidence-statement">{claim.statement}</p>

      <section className="evidence-block">
        <h4>Values</h4>
        {claim.value.length ? (
          <ul className="evidence-value-list">
            {claim.value.map((value) => (
              <ValueRow key={value.metric_id} value={value} />
            ))}
          </ul>
        ) : (
          <p className="detail-empty">No value recorded for this claim.</p>
        )}
      </section>

      <section className="evidence-block">
        <h4>Source</h4>
        <dl className="evidence-grid">
          <Meta label="Publisher" value={claim.source?.publisher ?? "Unknown"} />
          <Meta label="Class" value={claim.source?.source_class ?? "Unknown"} />
          <Meta label="Public URL" value={<SourceLink url={claim.source?.url ?? null} />} />
          <Meta
            label="Freshness"
            value={`${humaniseFreshness(claim.freshness.state)}${
              claim.freshness.age_days != null ? ` · ${claim.freshness.age_days}d` : ""
            }`}
          />
          <Meta label="Observed" value={formatDate(claim.freshness.observed_at)} />
        </dl>
      </section>

      <details className="evidence-technical">
        <summary>Technical provenance &amp; confidence</summary>
        <div className="evidence-technical-body">
          <section className="evidence-block">
            <h4>Confidence</h4>
            <p className="evidence-rationale">
              <strong>{claim.confidence}</strong>
              {detail?.score != null ? ` · score ${detail.score}` : " · no numeric score"}
              {detail?.derived ? " · evidence-derived" : " · not marked derived"}
            </p>
            {rationale.length ? (
              <ul className="unknown-list">
                {rationale.map((line, i) => (
                  <li key={i}>{line}</li>
                ))}
              </ul>
            ) : (
              <p className="detail-empty">No rationale supplied by the backend.</p>
            )}
            {inputs.length ? (
              <ul className="evidence-inputs">
                {inputs.map(([key, val]) => (
                  <li key={key}>
                    <code>{key}</code>: {String(val)}
                  </li>
                ))}
              </ul>
            ) : null}
          </section>

          <section className="evidence-block">
            <h4>Provenance</h4>
            {claim.provenance.length ? (
              <ul className="evidence-provenance">
                {claim.provenance.map((entry, i) => (
                  <li key={i}>
                    <div className="provenance-locator">
                      <code>{entry.field_path}</code>
                      <span className="chip">{entry.locator_kind}</span>
                      {entry.selector ? <code>{entry.selector}</code> : null}
                    </div>
                    {entry.quote ? <blockquote data-testid="provenance-quote">{entry.quote}</blockquote> : null}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="detail-empty">No provenance recorded for this claim.</p>
            )}
          </section>

          <section className="evidence-block">
            <h4>Captures</h4>
            {claim.evidence.length ? (
              <ul className="evidence-captures">
                {claim.evidence.map((capture) => (
                  <li key={capture.capture_hash}>
                    <code>{capture.capture_hash.slice(0, 12)}</code>{" "}
                    <span className={capture.snapshot_available ? "capture-ok" : "capture-missing"}>
                      {capture.snapshot_available ? "snapshot available" : "snapshot unavailable"}
                    </span>
                    {capture.fetched_at ? <span className="muted"> · fetched {formatDate(capture.fetched_at)}</span> : null}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="detail-empty">No capture recorded for this claim.</p>
            )}
            <p className="detail-hint">Capture identifiers only — snapshots stay on the server.</p>
          </section>
        </div>
      </details>
    </li>
  );
}

/**
 * F1: make a degraded history source visible. Never implies "no history" when
 * an endpoint actually errored, and never fabricates entries.
 */
function HistoryStatusNote({ status }: { status: HistoryStatus }) {
  const parts: string[] = [];
  if (status.claims === "error") parts.push("claims");
  if (status.events === "error") parts.push("change events");
  if (!parts.length) return null;
  return (
    <p className="detail-hint" data-testid="history-unavailable">
      History source unavailable ({parts.join(" + ")}); showing what the backend returned.
    </p>
  );
}

function History({ evidence, status }: { evidence: SurfaceEvidence; status: HistoryStatus }) {
  const history = buildHistory(evidence.claims ?? [], evidence.history ?? []);
  return (
    <section className="detail-section">
      <h3>History</h3>
      <HistoryStatusNote status={status} />
      {history.length ? (
        <ol className="evidence-history" data-testid="evidence-history">
          {history.map((item) => (
            <li key={item.id} className={`history-${item.kind}`}>
              <span className="history-date">{formatDate(item.date)}</span>
              <div className="history-body">
                <p className="history-title">{item.title}</p>
                <p className="history-meta">
                  <span className="chip">{item.kind === "change" ? item.eventType ?? "change" : "validated claim"}</span>
                  {item.sourceUrl ? (
                    <>
                      {" · "}
                      <SourceLink url={item.sourceUrl} label="source" />
                    </>
                  ) : null}
                </p>
              </div>
            </li>
          ))}
        </ol>
      ) : (
        <p className="detail-empty">No persisted claim or change history for this surface yet.</p>
      )}
    </section>
  );
}

function LatestChange({ evidence }: { evidence: SurfaceEvidence }) {
  const change = evidence.latest_change;
  if (!change) return null;
  return (
    <section className="detail-section">
      <h3>Latest material change</h3>
      <div className="latest-change" data-testid="latest-change">
        <span className="chip">{change.event_type}</span>
        <p className="latest-change-title">{change.title}</p>
        <p className="muted">
          Observed {formatDate(change.observed_at)} · Published {formatDate(change.published_at)}
        </p>
      </div>
    </section>
  );
}

/**
 * Per-surface evidence drill-down. Fetches the full payload lazily on mount via
 * the server action, then shows every validated claim (never `claims[0]`-only),
 * its values with explicit unknown states, the public source, confidence,
 * provenance behind expandable detail, the latest change and the chronological
 * history. Technical provenance is collapsed by default so the top stays a
 * concise summary.
 */
export function EvidenceDetail({ surfaceId, summary }: { surfaceId: string; summary?: SurfaceEvidence }) {
  const [detail, setDetail] = useState<SurfaceDetail | null>(summary ? { evidence: summary, historyStatus: { claims: "skipped", events: "skipped" } } : null);
  const [error, setError] = useState(false);

  useEffect(() => {
    let active = true;
    loadSurfaceDetail(surfaceId)
      .then((result) => {
        if (active) setDetail(result);
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
      <section className="detail-section">
        <h3>Evidence</h3>
        <p className="detail-empty" data-testid="evidence-error">
          Evidence detail could not be loaded. No data is invented.
        </p>
      </section>
    );
  }

  if (!detail) {
    return (
      <section className="detail-section">
        <h3>Evidence</h3>
        <p className="detail-empty" data-testid="evidence-loading">
          Loading evidence…
        </p>
      </section>
    );
  }

  const { evidence, historyStatus } = detail;
  const claims = evidence.claims ?? [];
  const lead = leadingClaim(claims);
  const hasEvents = (evidence.history?.length ?? 0) > 0;

  if (evidence.evidence_state === "no_evidence" || claims.length === 0) {
    // F5: no contradictory chrome. If change events exist, say so explicitly;
    // otherwise show only the no-evidence statement (no empty History block).
    return (
      <section className="detail-section">
        <h3>Evidence</h3>
        <p className="detail-lead" data-testid="no-evidence">
          <strong>No validated claim.</strong>{" "}
          {evidence.evidence_note ?? "No validated claim is linked to this surface yet."}
        </p>
        <HistoryStatusNote status={historyStatus} />
        {hasEvents ? (
          <>
            <p className="detail-hint">
              Change events exist for this surface, but none has been validated into a claim yet.
            </p>
            <History evidence={evidence} status={historyStatus} />
          </>
        ) : null}
      </section>
    );
  }

  return (
    <>
      <section className="detail-section">
        <h3>Evidence</h3>
        <p className="detail-lead" data-testid="evidence-summary">
          <strong>
            {claims.length} validated claim{claims.length === 1 ? "" : "s"}.
          </strong>{" "}
          {lead
            ? `Leading confidence ${lead.confidence}${
                lead.confidence_detail.score != null ? ` (${lead.confidence_detail.score})` : ""
              }.`
            : null}
        </p>
        <ul className="evidence-claims" data-testid="evidence-claims">
          {claims.map((claim, index) => (
            <ClaimCard key={claim.claim_id} claim={claim} index={index} />
          ))}
        </ul>
      </section>

      <LatestChange evidence={evidence} />
      <History evidence={evidence} status={historyStatus} />
    </>
  );
}
