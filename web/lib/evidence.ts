/**
 * Client for the read-only evidence API (issues #23/#46). Server-only: it makes
 * an HTTP call to the FastAPI evidence service. When no service is configured
 * the plane degrades to its explicit no-evidence state rather than inventing
 * data. The page render fetches the bulk projection in ONE request; per-surface
 * claim/event history is fetched lazily by the drill-down (see
 * `evidence-actions.ts`), so request volume never scales with the surface count.
 */
import type { SurfaceRow } from "@/lib/surfaces";

export const EVIDENCE_API_BASE = process.env.EVIDENCE_API_URL ?? "";

/** Recorded-fixture mode for tests/CI without the live API. Never set in prod. */
export const FIXTURE_MODE = process.env.EVIDENCE_FIXTURE === "1";

export interface EvidenceValue {
  metric_id: string;
  label: string;
  value_number: number | null;
  value_text: string | null;
  unit: string | null;
  window: string | null;
  scope: string | null;
  known: boolean;
}

export interface EvidenceClaim {
  claim_id: string;
  topic: string;
  statement: string;
  confidence: string;
  confidence_detail: {
    score: number | null;
    inputs: Record<string, number>;
    rationale: string[];
    derived: boolean;
  };
  value: EvidenceValue[];
  source: { publisher?: string | null; url?: string | null; source_class?: string | null };
  provenance: Array<{
    field_path: string;
    locator_kind: string;
    quote: string | null;
    selector: string | null;
  }>;
  evidence: Array<{ capture_hash: string; snapshot_available: boolean; fetched_at?: string | null }>;
  freshness: { state: string; age_days: number | null; observed_at: string | null };
}

/** One persisted material change event (`GET /events?surface=`). */
export interface EvidenceEvent {
  id: string;
  event_type: string;
  title: string;
  description?: string | null;
  surfaces?: string[];
  claims?: string[];
  evidence_urls?: string[] | null;
  observed_at?: string | null;
  published_at?: string | null;
  effective_from?: string | null;
  supersedes?: string | null;
  source_hash?: string | null;
}

/** A single row of the surface's chronological evidence/change history. */
export interface HistoryItem {
  id: string;
  kind: "claim" | "change";
  title: string;
  subtitle: string | null;
  /** Best available ISO timestamp; null when the backend has none. */
  date: string | null;
  claimId: string | null;
  eventType: string | null;
  sourceUrl: string | null;
}

export interface SurfaceEvidence {
  surface: string;
  evidence_state: "evidenced" | "no_evidence";
  evidence_note: string | null;
  claims: EvidenceClaim[];
  latest_change: {
    id: string;
    event_type: string;
    title: string;
    published_at: string | null;
    observed_at: string | null;
  } | null;
  /** Persisted change events for the history view (may be empty). */
  history?: EvidenceEvent[];
}

/** Per-endpoint outcome for the lazily-fetched history, so failure is visible. */
export interface HistoryStatus {
  claims: "ok" | "error" | "skipped";
  events: "ok" | "error" | "skipped";
}

export interface SurfaceDetail {
  evidence: SurfaceEvidence;
  historyStatus: HistoryStatus;
}

export const NO_EVIDENCE_NOTE =
  "No validated claim is linked to this surface yet. The plane does not invent provenance.";

/** Explicit no-evidence projection for a surface the API did not return. */
export function emptySurfaceEvidence(surfaceId: string): SurfaceEvidence {
  return {
    surface: surfaceId,
    evidence_state: "no_evidence",
    evidence_note: NO_EVIDENCE_NOTE,
    claims: [],
    latest_change: null,
    history: [],
  };
}

/** True when the backend gives neither a numeric nor a textual value. */
export function isUnknownValue(value: EvidenceValue): boolean {
  return value.value_number == null && value.value_text == null;
}

/** Human-readable value with an explicit "Unknown" state (never a blank cell). */
export function valueDisplay(value: EvidenceValue): string {
  if (isUnknownValue(value)) return "Unknown";
  if (value.value_text != null && value.value_text !== "") return value.value_text;
  if (value.value_number != null) return String(value.value_number);
  return "Unknown";
}

export function humaniseFreshness(state: string): string {
  switch (state) {
    case "fresh":
      return "Fresh";
    case "recent":
      return "Recent";
    case "aging":
      return "Aging";
    case "stale":
      return "Stale";
    default:
      return "Unknown freshness";
  }
}

/** ISO timestamp (or null) rendered as a plain date, never a fabricated one. */
export function formatDate(iso: string | null | undefined): string {
  if (!iso) return "Unknown";
  return iso.slice(0, 10);
}

/**
 * Merge persisted claims and change events into one chronological (newest
 * first) history. An event is linked to the claim it re-states when their
 * source/capture hash matches, so the history never duplicates a change that
 * is already represented as a validated claim.
 */
export function buildHistory(claims: EvidenceClaim[], events: EvidenceEvent[]): HistoryItem[] {
  const claimByCapture = new Map<string, string>();
  for (const claim of claims) {
    for (const capture of claim.evidence ?? []) {
      claimByCapture.set(capture.capture_hash, claim.claim_id);
    }
  }

  const linkedClaims = new Set<string>();
  const items: HistoryItem[] = [];

  for (const event of events ?? []) {
    const linked = event.source_hash ? claimByCapture.get(event.source_hash) ?? null : null;
    if (linked) linkedClaims.add(linked);
    items.push({
      id: `event:${event.id}`,
      kind: "change",
      title: event.title,
      subtitle: event.event_type,
      date: event.observed_at ?? event.published_at ?? event.effective_from ?? null,
      claimId: linked,
      eventType: event.event_type,
      sourceUrl: event.evidence_urls?.[0] ?? null,
    });
  }

  for (const claim of claims ?? []) {
    if (linkedClaims.has(claim.claim_id)) continue;
    items.push({
      id: `claim:${claim.claim_id}`,
      kind: "claim",
      title: claim.statement,
      subtitle: claim.topic,
      date: claim.freshness?.observed_at ?? null,
      claimId: claim.claim_id,
      eventType: null,
      sourceUrl: claim.source?.url ?? null,
    });
  }

  items.sort((a, b) => (b.date ?? "").localeCompare(a.date ?? "") || a.id.localeCompare(b.id));
  return items;
}

/** The claim that best represents the surface: highest confidence score wins. */
export function leadingClaim(claims: EvidenceClaim[]): EvidenceClaim | null {
  if (!claims.length) return null;
  return claims.reduce((best, claim) => {
    const bestScore = best.confidence_detail?.score ?? -1;
    const score = claim.confidence_detail?.score ?? -1;
    return score > bestScore ? claim : best;
  }, claims[0]);
}

/** Freshest claim timestamp across every claim on the surface. */
function newestObserved(claims: EvidenceClaim[]): string | null {
  return claims
    .map((claim) => claim.freshness?.observed_at ?? null)
    .filter((value): value is string => Boolean(value))
    .sort()
    .reverse()[0] ?? null;
}

/**
 * Overlays real evidence onto the registry rows. Only lightweight summary
 * fields reach the row (and therefore the client prop): the full claims,
 * provenance quotes, rationale and capture metadata are loaded lazily by the
 * drill-down, so the collapsed table never carries unbounded free text.
 */
export function applyEvidence(rows: SurfaceRow[], bySurface: Record<string, SurfaceEvidence>): SurfaceRow[] {
  return rows.map((row) => {
    const ev = bySurface[row.id] ?? emptySurfaceEvidence(row.id);
    const claims = ev.claims ?? [];
    if (ev.evidence_state === "no_evidence" || claims.length === 0) {
      return {
        ...row,
        evidenceStatus: "no_evidence",
        evidenceLabel: "No evidence",
        evidenceNote: ev.evidence_note ?? NO_EVIDENCE_NOTE,
        confidenceLabel: "Unknown — no validated claim",
        freshnessLabel: "No capture yet",
        evidenceClaimCount: 0,
      };
    }

    const lead = leadingClaim(claims)!;
    const newest = newestObserved(claims);
    const knownValues = claims.reduce((total, claim) => total + claim.value.filter((v) => !isUnknownValue(v)).length, 0);
    const valueLabel = claims
      .flatMap((claim) => claim.value)
      .filter((value) => !isUnknownValue(value))
      .map((value) => `${valueDisplay(value)}${value.unit ? " " + value.unit : ""}`)[0];

    return {
      ...row,
      evidenceStatus: "evidenced",
      evidenceLabel: `${claims.length} claim${claims.length === 1 ? "" : "s"}`,
      evidenceNote:
        `${claims.length} validated claim${claims.length === 1 ? "" : "s"}` +
        (knownValues ? ` — ${knownValues} value(s), e.g. ${valueLabel}.` : " — no known values yet.") +
        ` ${humaniseFreshness(lead.freshness.state)}.`,
      confidenceLabel: `${lead.confidence} (${lead.confidence_detail.score ?? "n/a"})`,
      freshnessLabel: newest ? `${humaniseFreshness(lead.freshness.state)} — ${newest.slice(0, 10)}` : "No capture date",
      evidenceClaimCount: claims.length,
    };
  });
}

interface FetchOutcome<T> {
  status: "ok" | "error";
  data: T | null;
  code?: number;
}

/** Fetch JSON and make a failure loud: log the status/URL, never swallow it. */
async function fetchJson<T>(path: string): Promise<FetchOutcome<T>> {
  try {
    const res = await fetch(`${EVIDENCE_API_BASE}${path}`, { cache: "no-store" });
    if (!res.ok) {
      console.error(`[evidence] GET ${path} failed: HTTP ${res.status}`);
      return { status: "error", data: null, code: res.status };
    }
    return { status: "ok", data: (await res.json()) as T };
  } catch (error) {
    console.error(`[evidence] GET ${path} failed:`, error);
    return { status: "error", data: null };
  }
}

/**
 * Bulk evidence projection for the whole plane. ONE request, independent of the
 * number of surfaces, cached with a short revalidate instead of `no-store`.
 * The response already carries each surface's claims, so no per-surface
 * fan-out is needed at render time.
 */
export async function fetchSurfaceEvidence(): Promise<Record<string, SurfaceEvidence>> {
  if (FIXTURE_MODE) {
    const { fixtureSurfaces } = await import("./evidence-fixtures");
    return fixtureSurfaces();
  }
  if (!EVIDENCE_API_BASE) return {};
  try {
    const res = await fetch(`${EVIDENCE_API_BASE}/surface-evidence`, { next: { revalidate: 60 } });
    if (!res.ok) {
      console.error(`[evidence] GET /surface-evidence failed: HTTP ${res.status}`);
      return {};
    }
    const body = (await res.json()) as { surfaces?: Record<string, SurfaceEvidence> };
    return body.surfaces ?? {};
  } catch (error) {
    console.error("[evidence] GET /surface-evidence failed:", error);
    return {};
  }
}

/**
 * Lazy full detail for ONE surface, fetched only when its drill-down opens.
 * Combines the surface evidence with claim/event history and reports which
 * endpoints failed so the UI can say so rather than implying "no history".
 */
export async function fetchSurfaceDetail(surfaceId: string): Promise<SurfaceDetail> {
  if (FIXTURE_MODE) {
    const { fixtureDetail } = await import("./evidence-fixtures");
    return fixtureDetail(surfaceId);
  }
  const empty = emptySurfaceEvidence(surfaceId);
  if (!EVIDENCE_API_BASE) {
    return { evidence: empty, historyStatus: { claims: "skipped", events: "skipped" } };
  }
  const encoded = encodeURIComponent(surfaceId);
  const [evidenceOutcome, claimsOutcome, eventsOutcome] = await Promise.all([
    fetchJson<SurfaceEvidence>(`/surfaces/${encoded}/evidence`),
    fetchJson<{ items?: EvidenceClaim[] }>(`/claims?surface=${encoded}&limit=100`),
    fetchJson<{ items?: EvidenceEvent[] }>(`/events?surface=${encoded}`),
  ]);

  const evidence = evidenceOutcome.data ?? empty;
  const byId = new Map<string, EvidenceClaim>();
  for (const claim of [...(evidence.claims ?? []), ...(claimsOutcome.data?.items ?? [])]) {
    byId.set(claim.claim_id, claim);
  }
  evidence.claims = [...byId.values()];
  evidence.history = eventsOutcome.data?.items ?? [];

  return {
    evidence,
    historyStatus: { claims: claimsOutcome.status, events: eventsOutcome.status },
  };
}
