/**
 * Read client for the landing intelligence views (issue #45): the latest
 * material change events (`GET /events`) and the weekly executive brief
 * (`GET /brief`). Server-only — it performs HTTP calls to the FastAPI evidence
 * service through the same base URL as `@/lib/evidence`.
 *
 * Every fetch reports an explicit outcome so the landing can distinguish a
 * genuinely empty result ("no material item qualifies") from an unreachable
 * backend ("the brief service is not reachable right now"). It never invents
 * data: an error yields `status: "error"` and the view says so.
 */
import { evidenceApiBase, type EvidenceEvent } from "./evidence";

export type IntelStatus = "ok" | "empty" | "error" | "unconfigured";

/** `GET /events` — newest-first persisted change events. */
export interface EventsOutcome {
  status: IntelStatus;
  items: EvidenceEvent[];
}

/** One item of the weekly executive brief. */
export interface BriefItem {
  change: string;
  why_it_matters: string;
  agency_action: string;
  confidence: string;
  significance: number;
  evidence_ids: string[];
  surfaces: string[];
  is_watch_item: boolean;
  effective_from?: string | null;
  published_at?: string | null;
  observed_at?: string | null;
}

/** `GET /brief` — the current restrained weekly brief. */
export interface Brief {
  state: "ready" | "empty";
  generated_at: string | null;
  window_start: string | null;
  window_end: string | null;
  items: BriefItem[];
  note?: string | null;
}

export interface BriefOutcome {
  status: IntelStatus;
  brief: Brief | null;
}

const NO_BASE = "EVIDENCE_API_URL is not configured";

/** Latest material change events, newest first. */
export async function fetchEvents(): Promise<EventsOutcome> {
  if (!evidenceApiBase()) {
    console.error(`[intel] GET /events skipped: ${NO_BASE}`);
    return { status: "unconfigured", items: [] };
  }
  try {
    const res = await fetch(`${evidenceApiBase()}/events`, { next: { revalidate: 60 } });
    if (!res.ok) {
      console.error(`[intel] GET /events failed: HTTP ${res.status}`);
      return { status: "error", items: [] };
    }
    const body = (await res.json()) as { items?: EvidenceEvent[] };
    const items = body.items ?? [];
    return { status: items.length ? "ok" : "empty", items };
  } catch (error) {
    console.error("[intel] GET /events failed:", error);
    return { status: "error", items: [] };
  }
}

/** The current weekly executive brief. */
export async function fetchBrief(): Promise<BriefOutcome> {
  if (!evidenceApiBase()) {
    console.error(`[intel] GET /brief skipped: ${NO_BASE}`);
    return { status: "unconfigured", brief: null };
  }
  try {
    const res = await fetch(`${evidenceApiBase()}/brief`, { next: { revalidate: 60 } });
    if (!res.ok) {
      console.error(`[intel] GET /brief failed: HTTP ${res.status}`);
      return { status: "error", brief: null };
    }
    const body = (await res.json()) as Brief;
    const state: IntelStatus = body.state === "empty" || !body.items?.length ? "empty" : "ok";
    return { status: state, brief: body };
  } catch (error) {
    console.error("[intel] GET /brief failed:", error);
    return { status: "error", brief: null };
  }
}
