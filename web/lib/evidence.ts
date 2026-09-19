/**
 * Client for the read-only evidence API (issue #23). Server-only: it makes an
 * HTTP call to the FastAPI evidence service. When no service is configured the
 * plane degrades to its explicit no-evidence state rather than inventing data.
 */
import type { SurfaceRow } from "@/lib/surfaces";

export const EVIDENCE_API_BASE = process.env.EVIDENCE_API_URL ?? "";

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
}

const NO_EVIDENCE_NOTE =
  "No validated claim is linked to this surface yet. The plane does not invent provenance.";

/** Explicit no-evidence projection for a surface the API did not return. */
export function emptySurfaceEvidence(surfaceId: string): SurfaceEvidence {
  return {
    surface: surfaceId,
    evidence_state: "no_evidence",
    evidence_note: NO_EVIDENCE_NOTE,
    claims: [],
    latest_change: null,
  };
}

function humaniseFreshness(state: string): string {
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

/**
 * Overlays real evidence onto the registry rows, in place of the placeholder
 * Evidence section. Registry fields are untouched; only evidence fields change,
 * and a surface with no claim keeps an explicit no-evidence state.
 */
export function applyEvidence(rows: SurfaceRow[], bySurface: Record<string, SurfaceEvidence>): SurfaceRow[] {
  return rows.map((row) => {
    const ev = bySurface[row.id] ?? emptySurfaceEvidence(row.id);
    const claim = ev.claims[0];
    if (ev.evidence_state === "no_evidence" || !claim) {
      return {
        ...row,
        evidenceStatus: "no_evidence",
        evidenceLabel: "No evidence",
        evidenceNote: ev.evidence_note ?? NO_EVIDENCE_NOTE,
        confidenceLabel: "Unknown — no validated claim",
        freshnessLabel: "No capture yet",
      };
    }
    const known = claim.value.find((v) => v.known);
    const valueLabel = known
      ? `${known.value_text ?? known.value_number}${known.unit ? " " + known.unit : ""}`
      : "Unknown value";
    return {
      ...row,
      evidenceStatus: "evidenced",
      evidenceLabel: `${claim.value.filter((v) => v.known).length} value(s)`,
      evidenceNote: `${claim.statement} — ${valueLabel}. ${humaniseFreshness(claim.freshness.state)}.`,
      confidenceLabel: `${claim.confidence} (${claim.confidence_detail.score ?? "n/a"})`,
      freshnessLabel:
        claim.freshness.observed_at != null
          ? `${humaniseFreshness(claim.freshness.state)} — ${claim.freshness.observed_at.slice(0, 10)}`
          : "No capture date",
    };
  });
}

/** Fetch the bulk evidence projection. A network error is an explicit no-evidence state. */
export async function fetchSurfaceEvidence(): Promise<Record<string, SurfaceEvidence>> {
  if (!EVIDENCE_API_BASE) return {};
  try {
    const res = await fetch(`${EVIDENCE_API_BASE}/surface-evidence`, { cache: "no-store" });
    if (!res.ok) return {};
    const body = (await res.json()) as { surfaces?: Record<string, SurfaceEvidence> };
    return body.surfaces ?? {};
  } catch {
    return {};
  }
}
