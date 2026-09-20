/**
 * Client contract for the marketer-first landscape + mechanics comparison
 * (Phase 2, issue #60). The projection is produced entirely by the backend
 * (`/landscape`, `/landscape/comparison`); this module only types that payload
 * and provides pure presentation helpers. It NEVER derives a mechanic, coverage
 * or comparison cell in React. Registry facts are labelled as registry metadata;
 * a comparison cell with no evidence is an explicit `unknown`.
 */
import { evidenceApiBase, fixtureMode } from "./evidence";
import type { EvidenceClass, MechanicsState } from "./mechanics";

export interface LandscapeSurface {
  id: string;
  name: string;
  vendor: string;
  type: string;
  type_label: string;
  priority: string;
  regions: string[];
  discovery_modes: string[];
  official_url: string | null;
  reach_metric: string | null;
  reach_claim_id: string | null;
  reach_confidence: string | null;
  evidenced_dimensions: number;
  dimension_count: number;
  coverage: Record<MechanicsState, number>;
  relevance: string;
}

export interface ComparisonCell {
  dimension: string;
  state: MechanicsState | string;
  statement: string | null;
  claim_id: string | null;
  evidence_class: EvidenceClass | string | null;
  confidence: string | null;
  unknown: boolean;
}

export interface ComparisonRow {
  dimension: string;
  label: string;
  definition: string;
  cells: Record<string, ComparisonCell>;
}

export interface LandscapeProjection {
  surfaces: LandscapeSurface[];
  comparison_surface_ids: string[];
  comparison: ComparisonRow[];
  dimension_count?: number;
}

export type LandscapeStatus = "ok" | "empty" | "error" | "unconfigured";

export interface LandscapeOutcome {
  status: LandscapeStatus;
  projection: LandscapeProjection | null;
}

export const LANDSCAPE_FETCH_TIMEOUT_MS = 4000;

/** The default comparison set (issue #60: ChatGPT, Gemini/AI Mode, Claude,
 *  Perplexity, DeepSeek + a regional/China surface). Every id is a registry id. */
export const DEFAULT_COMPARISON_IDS = [
  "chatgpt",
  "google-gemini",
  "google-ai-mode",
  "claude",
  "perplexity",
  "deepseek-chat",
] as const;

export const COMPARISON_MIN = 2;
export const COMPARISON_MAX = 6;

export async function fetchLandscape(): Promise<LandscapeOutcome> {
  if (fixtureMode()) {
    const { fixtureLandscape } = await import("./landscape-fixtures");
    return { status: "ok", projection: fixtureLandscape() };
  }
  if (!evidenceApiBase()) {
    console.error("[landscape] GET /landscape skipped: EVIDENCE_API_URL is not configured");
    return { status: "unconfigured", projection: null };
  }
  try {
    const res = await fetch(`${evidenceApiBase()}/landscape`, {
      next: { revalidate: 120 },
      signal: AbortSignal.timeout(LANDSCAPE_FETCH_TIMEOUT_MS),
    });
    if (!res.ok) {
      console.error(`[landscape] GET /landscape failed: HTTP ${res.status}`);
      return { status: "error", projection: null };
    }
    const body = (await res.json()) as LandscapeProjection;
    return { status: body.surfaces?.length ? "ok" : "empty", projection: body };
  } catch (error) {
    console.error("[landscape] GET /landscape failed:", error);
    return { status: "error", projection: null };
  }
}

/** Parse a comma-separated `surfaces` query param into a clean, capped id list. */
export function parseComparisonIds(raw: string | null | undefined): string[] {
  if (!raw) return [];
  const ids = [...new Set(raw.split(",").map((s) => s.trim()).filter(Boolean))];
  return ids.slice(0, COMPARISON_MAX);
}

/** A surface's coverage summary as a compact "7/13 evidenced" string. */
export function coverageLabel(surface: LandscapeSurface): string {
  return `${surface.evidenced_dimensions}/${surface.dimension_count} evidenced`;
}

/** Evidence classes present across a comparison column, for a confidence cue. */
export function columnEvidenceClasses(
  projection: LandscapeProjection,
  surfaceId: string,
): Set<string> {
  const out = new Set<string>();
  for (const row of projection.comparison) {
    const cell = row.cells[surfaceId];
    if (cell && !cell.unknown && cell.evidence_class) out.add(cell.evidence_class);
  }
  return out;
}

/** Unknown cells for a surface, kept explicit rather than hidden. */
export function unknownCellCount(projection: LandscapeProjection, surfaceId: string): number {
  return projection.comparison.filter((r) => r.cells[surfaceId]?.unknown).length;
}
