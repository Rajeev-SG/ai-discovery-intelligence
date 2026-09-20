/**
 * Client contract for the canonical mechanics projection (Phase 2, issue #56).
 *
 * The projection is produced entirely by the backend (`/mechanics`,
 * `/surfaces/{id}/mechanics`) from validated ledger claims. This module only
 * types that payload and provides pure presentation helpers — it NEVER derives
 * mechanics, states or evidence in React. Unknown is a first-class state the
 * backend emits explicitly; the UI must render it as information.
 */
import { evidenceApiBase } from "./evidence";

export type MechanicsState = "known" | "partially_known" | "conflicting" | "unknown";

export type EvidenceClass =
  | "official_documentation"
  | "independent_research"
  | "controlled_observation";

export interface MechanicsEvidence {
  claim_id: string;
  source_id: string | null;
  publisher: string | null;
  url: string | null;
  source_class: string;
  evidence_class: EvidenceClass | string;
  published_at: string | null;
  observed_at: string | null;
  effective_from: string | null;
  confidence: string;
  confidence_score: number | null;
  measurement_mode: string | null;
  methodology_notes: string | null;
  limitations: string[];
  modes: string[];
  regions: string[];
  relates_to_claim_id: string | null;
  relationship: string;
}

export interface MechanicsAssertion {
  statement: string;
  state: MechanicsState;
  conflict_note: string | null;
  evidence: MechanicsEvidence[];
}

export interface MechanicsDimension {
  dimension: string;
  label: string;
  definition: string;
  state: MechanicsState;
  note: string;
  assertions: MechanicsAssertion[];
}

export interface SurfaceMechanics {
  surface: string;
  dimensions: MechanicsDimension[];
  coverage: Record<MechanicsState, number>;
  evidenced_dimension_count: number;
  dimension_count: number;
}

export interface MechanicsProjection {
  dimension_count: number;
  count: number;
  surfaces: Record<string, SurfaceMechanics>;
  /** Diagnostic: claim surface ids absent from the registry (drift, not evidence). */
  unmapped_claim_surfaces?: Record<string, string[]>;
}

export type MechanicsStatus = "ok" | "empty" | "error" | "unconfigured";

export interface MechanicsOutcome {
  status: MechanicsStatus;
  projection: MechanicsProjection | null;
}

export const MECHANICS_FETCH_TIMEOUT_MS = 4000;

/** The three marketer-facing evidence classes, in trust order. */
export const EVIDENCE_CLASS_LABELS: Record<string, string> = {
  official_documentation: "Vendor-documented",
  independent_research: "Independently researched",
  controlled_observation: "Directly observed",
};

export function evidenceClassLabel(value: string): string {
  return EVIDENCE_CLASS_LABELS[value] ?? value.replace(/_/g, " ");
}

export const MECHANICS_STATE_LABELS: Record<MechanicsState, string> = {
  known: "Known",
  partially_known: "Partial",
  conflicting: "Conflicting",
  unknown: "Unknown",
};

/**
 * Fetch the whole mechanics projection in one request. Server-only. Reports an
 * explicit outcome so an unreachable backend is never rendered as "unknown" data.
 */
export async function fetchMechanics(): Promise<MechanicsOutcome> {
  if (!evidenceApiBase()) {
    console.error("[mechanics] GET /mechanics skipped: EVIDENCE_API_URL is not configured");
    return { status: "unconfigured", projection: null };
  }
  try {
    const res = await fetch(`${evidenceApiBase()}/mechanics`, {
      next: { revalidate: 120 },
      signal: AbortSignal.timeout(MECHANICS_FETCH_TIMEOUT_MS),
    });
    if (!res.ok) {
      console.error(`[mechanics] GET /mechanics failed: HTTP ${res.status}`);
      return { status: "error", projection: null };
    }
    const body = (await res.json()) as MechanicsProjection;
    return { status: body.count ? "ok" : "empty", projection: body };
  } catch (error) {
    console.error("[mechanics] GET /mechanics failed:", error);
    return { status: "error", projection: null };
  }
}

/** Dimensions that carry any evidence, newest state first — pure helper. */
export function evidencedDimensions(surface: SurfaceMechanics | null | undefined): MechanicsDimension[] {
  if (!surface) return [];
  return surface.dimensions.filter((d) => d.state !== "unknown");
}

/** The dominant evidence class across a dimension's assertions, for a badge. */
export function dimensionEvidenceClass(dimension: MechanicsDimension): EvidenceClass | null {
  const order: EvidenceClass[] = [
    "official_documentation",
    "controlled_observation",
    "independent_research",
  ];
  const present = new Set<string>();
  for (const a of dimension.assertions) for (const e of a.evidence) present.add(e.evidence_class);
  for (const cls of order) if (present.has(cls)) return cls;
  return null;
}
