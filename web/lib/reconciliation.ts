/**
 * Client-safe projection of the canonical persisted reconciliation ledger
 * (issue #47). This module holds the types, the read-only API fetch, and the
 * `claim_ids` -> claim join.
 *
 * Reconciliation semantics live in the backend (`GET /reconciliation`). This
 * module never re-derives a state, relationship or confidence adjustment — it
 * only resolves the opaque `<claim_id>:<metric_id>` references back to the real
 * claims and metrics so the UI can render both sides of a relationship side by
 * side without collapsing them into a single "truth".
 */

export const EVIDENCE_API_BASE = process.env.EVIDENCE_API_URL ?? "";

/** The canonical relationship states emitted by the backend. */
export type ReconciliationState =
  | "compatible_support"
  | "directional_support"
  | "methodologically_incomparable"
  | "temporal_update"
  | "material_conflict"
  | "possible_transient_change"
  | "unresolved";

export type ReconciliationRelationship =
  | "supports"
  | "updates"
  | "contradicts"
  | "supersedes"
  | "contextualises";

/** One persisted relationship between two or more claims. */
export interface ReconciliationItem {
  claim_ids: string[];
  state: ReconciliationState;
  relationship: ReconciliationRelationship;
  confidence_adjustment: number | null;
  differences: string[];
  unknown_dimensions: string[];
  interpretation: string;
}

export interface ReconciliationResponse {
  count: number;
  items: ReconciliationItem[];
}

/** A claim value/metric as returned by `GET /claims`. */
export interface ReconClaimValue {
  metric_id: string;
  label: string;
  value_number: number | null;
  value_text: string | null;
  unit: string | null;
  window: string | null;
  scope: string | null;
  known: boolean;
}

/** The subset of a claim the reconciliation view renders. */
export interface ReconClaim {
  claim_id: string;
  topic: string;
  statement: string;
  status?: string | null;
  relationship?: string | null;
  surfaces?: string[];
  value: ReconClaimValue[];
  source?: {
    publisher?: string | null;
    url?: string | null;
    source_class?: string | null;
  } | null;
  dates?: {
    measured_window?: string | null;
    observed_at?: string | null;
    published_at?: string | null;
  } | null;
  freshness?: { state?: string | null; age_days?: number | null } | null;
}

/** An unresolved `<claim_id>:<metric_id>` reference. */
export interface ClaimRef {
  raw: string;
  claim_id: string;
  metric_id: string | null;
}

/** Presentation bucket derived from the canonical state (never re-decided). */
export type StateCategory = "compatible" | "temporal" | "incomparable" | "conflict" | "unresolved";

/**
 * Split a reconciliation `claim_ids` entry into its claim and metric ids.
 * Entries look like `"<claim_id>:<metric_id>"`; a malformed entry with no
 * suffix still resolves to the claim with a null metric.
 */
export function splitClaimRef(raw: string): ClaimRef {
  const idx = raw.indexOf(":");
  if (idx === -1) return { raw, claim_id: raw, metric_id: null };
  const metric = raw.slice(idx + 1);
  return { raw, claim_id: raw.slice(0, idx), metric_id: metric.length > 0 ? metric : null };
}

/** Index claims by `claim_id` for O(1) join. Later duplicates win (API is canonical). */
export function indexClaims(claims: readonly ReconClaim[]): Map<string, ReconClaim> {
  const byId = new Map<string, ReconClaim>();
  for (const claim of claims) byId.set(claim.claim_id, claim);
  return byId;
}

/** Map a canonical state to its presentation bucket. Purely a lookup. */
export function stateCategory(state: ReconciliationState): StateCategory {
  switch (state) {
    case "compatible_support":
    case "directional_support":
      return "compatible";
    case "temporal_update":
    case "possible_transient_change":
      return "temporal";
    case "methodologically_incomparable":
      return "incomparable";
    case "material_conflict":
      return "conflict";
    case "unresolved":
    default:
      return "unresolved";
  }
}

/** A contested relationship is one whose state the backend flags as conflict/unresolved. */
export function isContested(state: ReconciliationState): boolean {
  return state === "material_conflict" || state === "unresolved";
}

export interface ResolvedSide {
  ref: ClaimRef;
  claim: ReconClaim | null;
  metric: ReconClaimValue | null;
  /** First surface id for the claim, used to link back into evidence detail. */
  surface: string | null;
  /** True when this side's evidence is superseded/updated by the other side. */
  superseded: boolean;
  /**
   * True when the claims ledger could not be fetched at all. Distinguishes
   * "the ledger is unreachable" from "this claim is genuinely absent", so the
   * UI never implies a claim does not exist when it merely could not be read.
   */
  ledgerUnavailable: boolean;
}

export interface ResolvedRelationship {
  item: ReconciliationItem;
  sides: ResolvedSide[];
  category: StateCategory;
  contested: boolean;
}

/** The observation instant used to order update-style relationships. */
function observedAt(claim: ReconClaim | null): string | null {
  return claim?.dates?.observed_at ?? null;
}

/**
 * Mark the superseded side(s) for relationships that assert precedence
 * (`supersedes` / `updates`) and only when both sides carry a persisted
 * observation time. `possible_transient_change` does not assert that one side
 * supersedes the other, so it never marks a side. When the timestamps are
 * missing or equal we mark nothing rather than guessing which side is older —
 * the reviewer's rule is "unknown which side is newer", rendered as-is.
 */
function markSuperseded(item: ReconciliationItem, sides: ResolvedSide[]): void {
  const assertsPrecedence = item.relationship === "supersedes" || item.relationship === "updates";
  if (!assertsPrecedence || sides.length < 2) return;
  const times = sides.map((s) => observedAt(s.claim));
  if (times.some((t) => t == null)) return;
  const known = times as string[];
  const newest = known.reduce((a, b) => (a > b ? a : b));
  const oldest = known.reduce((a, b) => (a < b ? a : b));
  if (newest === oldest) return;
  sides.forEach((side, i) => {
    if (times[i] !== newest) side.superseded = true;
  });
}

/** Resolve one persisted relationship against the claim ledger. */
export function joinRelationship(
  item: ReconciliationItem,
  byId: Map<string, ReconClaim>,
  ledgerUnavailable = false,
): ResolvedRelationship {
  const sides: ResolvedSide[] = item.claim_ids.map((raw) => {
    const ref = splitClaimRef(raw);
    const claim = byId.get(ref.claim_id) ?? null;
    const metric =
      claim && ref.metric_id ? claim.value.find((v) => v.metric_id === ref.metric_id) ?? null : null;
    return {
      ref,
      claim,
      metric,
      surface: claim?.surfaces && claim.surfaces.length > 0 ? claim.surfaces[0] : null,
      superseded: false,
      ledgerUnavailable,
    };
  });
  markSuperseded(item, sides);
  return {
    item,
    sides,
    category: stateCategory(item.state),
    contested: isContested(item.state),
  };
}

/**
 * Join a full reconciliation response against the claim ledger. When the claim
 * ledger is unreachable (`claims === null`) the relationships are still
 * rendered — each side is flagged `ledgerUnavailable` so the UI says the ledger
 * could not be read rather than implying the claim does not exist.
 */
export function joinReconciliation(
  response: ReconciliationResponse,
  claims: readonly ReconClaim[] | null,
): ResolvedRelationship[] {
  const byId = indexClaims(claims ?? []);
  const ledgerUnavailable = claims === null;
  return response.items.map((item) => joinRelationship(item, byId, ledgerUnavailable));
}

/** Human label for a relationship verb. */
export function relationshipLabel(relationship: ReconciliationRelationship): string {
  switch (relationship) {
    case "supports":
      return "Supports";
    case "updates":
      return "Updates";
    case "contradicts":
      return "Contradicts";
    case "supersedes":
      return "Supersedes";
    case "contextualises":
      return "Contextualises";
    default:
      return relationship;
  }
}

/** Human label for a canonical state. */
export function stateLabel(state: ReconciliationState): string {
  return state.replace(/_/g, " ");
}

/** Human label for a context dimension key. */
export function dimensionLabel(dimension: string): string {
  return dimension.replace(/_/g, " ");
}

/** Render a claim value, never inventing a number the ledger does not hold. */
export function formatValue(value: ReconClaimValue | null): string {
  if (!value || !value.known) return "Unknown value";
  const number = value.value_text ?? (value.value_number != null ? String(value.value_number) : null);
  if (number == null) return "Unknown value";
  return value.unit ? `${number} ${value.unit}`.trim() : number;
}

/** Render a confidence adjustment with an explicit sign, or "none". */
export function formatAdjustment(adjustment: number | null): string {
  if (adjustment == null) return "none";
  const rounded = Math.round(adjustment * 100) / 100;
  if (rounded === 0) return "0";
  return `${rounded > 0 ? "+" : "\u2212"}${Math.abs(rounded)}`;
}

/**
 * Link back into the evidence surface route (detail drill-down lives in #46).
 * The registry matrix moved to `/surfaces` in issue #45.
 */
export function surfaceHref(surface: string): string {
  return `/surfaces?surface=${encodeURIComponent(surface)}`;
}

function normalizeClaims(body: unknown): ReconClaim[] {
  if (Array.isArray(body)) return body as ReconClaim[];
  if (body && typeof body === "object") {
    const record = body as Record<string, unknown>;
    for (const key of ["items", "claims"]) {
      const value = record[key];
      if (Array.isArray(value)) return value as ReconClaim[];
    }
  }
  return [];
}

/** Timeout for the evidence API so a hanging upstream cannot stall the page. */
export const EVIDENCE_FETCH_TIMEOUT_MS = 5000;

/** Fetch the canonical reconciliation ledger. Returns null on any failure. */
export async function fetchReconciliation(): Promise<ReconciliationResponse | null> {
  if (!EVIDENCE_API_BASE) return null;
  try {
    const res = await fetch(`${EVIDENCE_API_BASE}/reconciliation`, {
      cache: "no-store",
      signal: AbortSignal.timeout(EVIDENCE_FETCH_TIMEOUT_MS),
    });
    if (!res.ok) return null;
    const body = (await res.json()) as { count?: number; items?: ReconciliationItem[] };
    return { count: body.count ?? body.items?.length ?? 0, items: body.items ?? [] };
  } catch {
    return null;
  }
}

/**
 * Fetch every claim so `claim_ids` entries can be resolved. Returns null when
 * the ledger could not be fetched (unlike an empty ledger, which returns `[]`),
 * so the caller can distinguish "unreachable" from "no claims".
 */
export async function fetchClaims(): Promise<ReconClaim[] | null> {
  if (!EVIDENCE_API_BASE) return null;
  try {
    const res = await fetch(`${EVIDENCE_API_BASE}/claims`, {
      cache: "no-store",
      signal: AbortSignal.timeout(EVIDENCE_FETCH_TIMEOUT_MS),
    });
    if (!res.ok) return null;
    return normalizeClaims(await res.json());
  } catch {
    return null;
  }
}
