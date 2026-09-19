import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { fetchSurfaceDetail } from "../lib/evidence";

/**
 * F1'/F4': drive the real `fetchSurfaceDetail` (merge + dedup + status) with a
 * stubbed `fetch`. This is the primary-endpoint failure path review #1 flagged:
 * a 500 on `/surfaces/{id}/evidence` must be surfaced as an error state, never
 * presented as a validated "no claim".
 */
const BASE = "http://evidence.test";

function jsonResponse(body: unknown, status = 200) {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  } as unknown as Response;
}

const claim = {
  claim_id: "c1",
  topic: "crawler_index_policy",
  statement: "Primary claim.",
  confidence: "medium",
  confidence_detail: { score: 0.5, inputs: {}, rationale: [], derived: true },
  value: [
    { metric_id: "m1", label: "T", value_number: 24, value_text: null, unit: "h", window: "w", scope: "s", known: true },
  ],
  source: { publisher: "Pub", url: "https://example.test/a", source_class: "official" },
  provenance: [{ field_path: "f", locator_kind: "verbatim_quote", quote: "q", selector: null }],
  evidence: [{ capture_hash: "cap-1", snapshot_available: true, fetched_at: "2026-09-19T00:00:00Z" }],
  freshness: { state: "fresh", age_days: 0, observed_at: "2026-09-19T00:00:00Z" },
};

const secondaryClaim = {
  ...claim,
  claim_id: "c2",
  statement: "Secondary claim from /claims.",
  // Distinct capture so it does not alias c1's provenance capture.
  evidence: [{ capture_hash: "cap-2", snapshot_available: true, fetched_at: "2026-09-19T00:00:00Z" }],
};

beforeEach(() => {
  process.env.EVIDENCE_API_URL = BASE;
  delete process.env.EVIDENCE_FIXTURE;
});
afterEach(() => {
  vi.unstubAllGlobals();
  delete process.env.EVIDENCE_API_URL;
});

describe("fetchSurfaceDetail (all sources ok)", () => {
  it("merges primary claims with /claims and links an event to its claim by capture_hash", async () => {
    const fetchMock = vi.fn(async (url: string) => {
      const u = String(url);
      if (u.includes("/surfaces/chatgpt/evidence")) {
        return jsonResponse({ surface: "chatgpt", evidence_state: "evidenced", evidence_note: null, claims: [claim], latest_change: null });
      }
      if (u.includes("/claims")) return jsonResponse({ items: [secondaryClaim] });
      if (u.includes("/events")) {
        return jsonResponse({ items: [{ id: "e1", event_type: "crawler_policy", title: "Linked change", source_hash: "cap-1", observed_at: "2026-09-19T00:00:00Z" }] });
      }
      return jsonResponse({}, 404);
    });
    vi.stubGlobal("fetch", fetchMock);

    const detail = await fetchSurfaceDetail("chatgpt");

    expect(detail.status).toEqual({ evidence: "ok", claims: "ok", events: "ok" });
    // Dedup + merge: both claims, no duplicate for the shared claim_id.
    expect(detail.evidence.claims.map((c) => c.claim_id).sort()).toEqual(["c1", "c2"]);
    expect(detail.evidence.history).toHaveLength(1);
    // Real linking code keys off capture_hash: the event links to c1.
    const { buildHistory } = await import("../lib/evidence");
    const history = buildHistory(detail.evidence.claims, detail.evidence.history ?? []);
    expect(history.find((h) => h.kind === "change")?.claimId).toBe("c1");
  });
});

describe("fetchSurfaceDetail (primary endpoint fails)", () => {
  it("surfaces the primary-endpoint error and never reports a validated no-evidence state", async () => {
    const fetchMock = vi.fn(async (url: string) => {
      const u = String(url);
      if (u.includes("/surfaces/chatgpt/evidence")) return jsonResponse("Internal Server Error", 500);
      if (u.includes("/claims")) return jsonResponse({ items: [] });
      if (u.includes("/events")) return jsonResponse({ items: [] });
      return jsonResponse({}, 404);
    });
    vi.stubGlobal("fetch", fetchMock);

    const detail = await fetchSurfaceDetail("chatgpt");

    // (1)/(2) the failure is tracked and distinguishable from empty.
    expect(detail.status.evidence).toBe("error");
    expect(detail.evidence.evidence_state).toBe("no_evidence");

    const { statusProblems } = await import("../lib/evidence");
    expect(statusProblems(detail.status)).toContain("surface evidence");
  });

  it("does not synthesize a no-evidence verdict when a secondary endpoint still returns claims", async () => {
    const fetchMock = vi.fn(async (url: string) => {
      const u = String(url);
      if (u.includes("/surfaces/chatgpt/evidence")) return jsonResponse("boom", 500);
      if (u.includes("/claims")) return jsonResponse({ items: [secondaryClaim] });
      if (u.includes("/events")) return jsonResponse({ items: [] });
      return jsonResponse({}, 404);
    });
    vi.stubGlobal("fetch", fetchMock);

    const detail = await fetchSurfaceDetail("chatgpt");

    expect(detail.status.evidence).toBe("error");
    // (3) real claim data was obtained, so the state is evidenced, not empty.
    expect(detail.evidence.evidence_state).toBe("evidenced");
    expect(detail.evidence.evidence_note).toBeNull();
    expect(detail.evidence.claims.map((c) => c.claim_id)).toEqual(["c2"]);
  });
});
