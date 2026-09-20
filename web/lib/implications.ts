/**
 * Client contract for the marketing implications read path (Phase 2, issue #59).
 *
 * The implications are derived entirely by the backend (`/implications`,
 * `/surfaces/{id}/implications`) from validated mechanics/evidence. This module
 * only types that payload and provides pure presentation helpers — it NEVER
 * derives an implication, a confidence or a significance in React. An
 * evidence-free or non-actionable surface arrives as an explicit `monitor_only`
 * state, which the UI renders as information.
 */
import { evidenceApiBase, fixtureMode } from "./evidence";

export type ImplicationFamily =
  | "crawlability_eligibility"
  | "indexability_freshness"
  | "citation_visibility"
  | "topic_coverage"
  | "structured_data_feed"
  | "commerce_shopping"
  | "local"
  | "social_community"
  | "referral_measurement"
  | "platform_prioritisation"
  | "monitor";

export type Actionability = "high" | "medium" | "low";

export interface Implication {
  family: ImplicationFamily | string;
  action: string;
  rationale: string;
  supporting_claim_ids: string[];
  supporting_dimensions: string[];
  surfaces: string[];
  modes: string[];
  regions: string[];
  confidence: string;
  actionability: Actionability | string;
  significance: number;
  contradicting_claim_ids: string[];
  monitor_only: boolean;
  note: string;
}

export interface SurfaceImplications {
  surface: string;
  monitor_only: boolean;
  note: string;
  implications: Implication[];
}

export interface ImplicationsProjection {
  count: number;
  surfaces: Record<string, SurfaceImplications>;
  cross_surface: Implication[];
}

export type ImplicationsStatus = "ok" | "empty" | "error" | "unconfigured";

export interface ImplicationsOutcome {
  status: ImplicationsStatus;
  projection: ImplicationsProjection | null;
}

export const IMPLICATIONS_FETCH_TIMEOUT_MS = 4000;

/** Marketer labels for each action family. Backend emits the family; this labels it. */
export const FAMILY_LABELS: Record<string, string> = {
  crawlability_eligibility: "Eligibility & crawlability",
  indexability_freshness: "Indexability & freshness",
  citation_visibility: "Citation visibility",
  topic_coverage: "Query & topic coverage",
  structured_data_feed: "Structured data & feeds",
  commerce_shopping: "Commerce & shopping",
  local: "Local",
  social_community: "Social & community",
  referral_measurement: "Referral & measurement",
  platform_prioritisation: "Platform prioritisation",
  monitor: "Monitor only",
};

export function familyLabel(value: string): string {
  return FAMILY_LABELS[value] ?? value.replace(/_/g, " ");
}

export const ACTIONABILITY_LABELS: Record<string, string> = {
  high: "Directly actionable",
  medium: "Actionable with investigation",
  low: "Informational",
};

export function actionabilityLabel(value: string): string {
  return ACTIONABILITY_LABELS[value] ?? value;
}

export const ACTIONABILITY_ORDER: Record<string, number> = { high: 3, medium: 2, low: 1 };

/** Fetch the whole implications projection in one request. Server-only. */
export async function fetchImplications(): Promise<ImplicationsOutcome> {
  if (process.env.EVIDENCE_FIXTURE === "all-monitor") {
    const { fixtureImplicationsAllMonitor } = await import("./implications-fixtures");
    return { status: "ok", projection: fixtureImplicationsAllMonitor() };
  }
  if (fixtureMode()) {
    const { fixtureImplications } = await import("./implications-fixtures");
    return { status: "ok", projection: fixtureImplications() };
  }
  if (!evidenceApiBase()) {
    console.error("[implications] GET /implications skipped: EVIDENCE_API_URL is not configured");
    return { status: "unconfigured", projection: null };
  }
  try {
    const res = await fetch(`${evidenceApiBase()}/implications`, {
      next: { revalidate: 120 },
      signal: AbortSignal.timeout(IMPLICATIONS_FETCH_TIMEOUT_MS),
    });
    if (!res.ok) {
      console.error(`[implications] GET /implications failed: HTTP ${res.status}`);
      return { status: "error", projection: null };
    }
    const body = (await res.json()) as ImplicationsProjection;
    return { status: body.count ? "ok" : "empty", projection: body };
  } catch (error) {
    console.error("[implications] GET /implications failed:", error);
    return { status: "error", projection: null };
  }
}

/** Surfaces that carry at least one action, in the backend's own order. */
export function actionableSurfaces(
  projection: ImplicationsProjection | null,
): SurfaceImplications[] {
  if (!projection) return [];
  // A monitor implication is a structured no-action result, so a surface counts
  // as actionable only when it has a non-monitor implication.
  return Object.values(projection.surfaces).filter((s) =>
    s.implications.some((i) => !i.monitor_only),
  );
}

/** Cross-surface implications sorted most-actionable, most-significant first. */
export function rankedImplications(
  projection: ImplicationsProjection | null,
): Implication[] {
  if (!projection) return [];
  return [...projection.cross_surface].sort(
    (a, b) =>
      (ACTIONABILITY_ORDER[b.actionability] ?? 0) - (ACTIONABILITY_ORDER[a.actionability] ?? 0) ||
      b.significance - a.significance,
  );
}
