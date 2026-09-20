import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { changeWindow, fetchBrief, fetchEvents } from "../lib/intel";

const ORIGINAL = process.env.EVIDENCE_API_URL;

afterEach(() => {
  process.env.EVIDENCE_API_URL = ORIGINAL;
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("fetchEvents", () => {
  it("is unconfigured (not an error, not empty) when no API base is set", async () => {
    delete process.env.EVIDENCE_API_URL;
    const outcome = await fetchEvents();
    expect(outcome.status).toBe("unconfigured");
    expect(outcome.items).toEqual([]);
  });

  it("returns events newest-first and reports ok", async () => {
    process.env.EVIDENCE_API_URL = "http://example.test";
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        new Response(JSON.stringify({ items: [{ id: "a" }, { id: "b" }] }), { status: 200 }),
      ),
    );
    const outcome = await fetchEvents();
    expect(outcome.status).toBe("ok");
    expect(outcome.items.map((e) => e.id)).toEqual(["a", "b"]);
  });

  it("reports empty (distinct from error) when the feed has no items", async () => {
    process.env.EVIDENCE_API_URL = "http://example.test";
    vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify({ items: [] }), { status: 200 })));
    const outcome = await fetchEvents();
    expect(outcome.status).toBe("empty");
  });

  it("reports error on a failed response rather than showing empty data", async () => {
    process.env.EVIDENCE_API_URL = "http://example.test";
    vi.stubGlobal("fetch", vi.fn(async () => new Response("nope", { status: 503 })));
    const outcome = await fetchEvents();
    expect(outcome.status).toBe("error");
    expect(outcome.items).toEqual([]);
  });
});

describe("fetchBrief", () => {
  it("distinguishes an empty brief (state:'empty') from an unavailable backend", async () => {
    process.env.EVIDENCE_API_URL = "http://example.test";
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        new Response(
          JSON.stringify({ state: "empty", generated_at: null, window_start: null, window_end: null, items: [] }),
          { status: 200 },
        ),
      ),
    );
    const outcome = await fetchBrief();
    expect(outcome.status).toBe("empty");
    expect(outcome.brief?.state).toBe("empty");
  });

  it("returns a ready brief with its items", async () => {
    process.env.EVIDENCE_API_URL = "http://example.test";
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        new Response(
          JSON.stringify({
            state: "ready",
            generated_at: "2026-09-19T00:00:00Z",
            window_start: "2026-09-12T00:00:00Z",
            window_end: "2026-09-19T00:00:00Z",
            items: [
              {
                change: "c",
                why_it_matters: "w",
                agency_action: "a",
                confidence: "medium",
                significance: 3.7,
                evidence_ids: ["e1"],
                surfaces: ["chatgpt"],
                is_watch_item: false,
              },
            ],
          }),
          { status: 200 },
        ),
      ),
    );
    const outcome = await fetchBrief();
    expect(outcome.status).toBe("ok");
    expect(outcome.brief?.items).toHaveLength(1);
  });

  it("reports error (not empty) when the brief endpoint fails", async () => {
    process.env.EVIDENCE_API_URL = "http://example.test";
    vi.stubGlobal("fetch", vi.fn(async () => new Response("boom", { status: 500 })));
    const outcome = await fetchBrief();
    expect(outcome.status).toBe("error");
    expect(outcome.brief).toBeNull();
  });

  it("is unconfigured when no API base is set", async () => {
    delete process.env.EVIDENCE_API_URL;
    const outcome = await fetchBrief();
    expect(outcome.status).toBe("unconfigured");
  });
});

describe("event type taxonomy (review F1)", () => {
  // Mirrors the backend EventType enum in src/ai_discovery/change_events.py.
  const BACKEND_EVENT_TYPES = [
    "product_launch",
    "retrieval_or_index_change",
    "audience_shift",
    "citation_source_shift",
    "crawler_policy",
    "commerce_ads",
    "referral_measurement",
    "correction_retraction",
  ];

  it("maps every backend EventType to a human label", async () => {
    const { EVENT_TYPE_LABELS, eventTypeLabel } = await import("../lib/intel");
    for (const value of BACKEND_EVENT_TYPES) {
      expect(EVENT_TYPE_LABELS[value], `missing label for ${value}`).toBeTruthy();
      expect(eventTypeLabel(value)).toBe(EVENT_TYPE_LABELS[value]);
    }
  });

  it("falls back to consistent Title-Case for unmapped taxonomy values", async () => {
    const { eventTypeLabel, titleCaseEventType } = await import("../lib/intel");
    expect(eventTypeLabel("some_new_event_type")).toBe("Some New Event Type");
    expect(titleCaseEventType("a_b_c")).toBe("A B C");
    // Never emits raw snake_case or lowercase-initial text.
    expect(eventTypeLabel("brand_new_thing")).not.toContain("_");
    expect(eventTypeLabel("brand_new_thing")[0]).toBe(eventTypeLabel("brand_new_thing")[0].toUpperCase());
  });
});

describe("fetch timeout (review F2)", () => {
  it("aborts a hung request and returns the error outcome, not a hang", async () => {
    process.env.EVIDENCE_API_URL = "http://example.test";
    vi.stubGlobal(
      "fetch",
      vi.fn(
        (_url: string, init?: RequestInit) =>
          new Promise<Response>((_resolve, reject) => {
            // Never resolves; only the abort signal can settle it.
            init?.signal?.addEventListener("abort", () =>
              reject(new DOMException("The operation was aborted.", "AbortError")),
            );
          }),
      ),
    );
    const { fetchEvents, INTEL_FETCH_TIMEOUT_MS } = await import("../lib/intel");
    expect(INTEL_FETCH_TIMEOUT_MS).toBeLessThanOrEqual(3000);
    const outcome = await fetchEvents();
    expect(outcome.status).toBe("error");
    expect(outcome.items).toEqual([]);
  }, 10_000);
});

describe("clampText (review F5)", () => {
  it("truncates long prose and leaves short prose untouched", async () => {
    const { clampText } = await import("../lib/intel");
    expect(clampText("short")).toBe("short");
    const long = "x".repeat(500);
    expect(clampText(long, 320).length).toBeLessThanOrEqual(321);
    expect(clampText(long, 320).endsWith("…")).toBe(true);
  });
});


describe("changeWindow truncation (issue #55 review)", () => {
  const items = Array.from({ length: 12 }, (_, i) => i);
  it("does not disclose a short feed", () => {
    const w = changeWindow([1, 2, 3], 5);
    expect(w.truncated).toBe(false);
    expect(w.shown).toHaveLength(3);
    expect(w.total).toBe(3);
  });
  it("discloses and caps a long feed", () => {
    const w = changeWindow(items, 5);
    expect(w.truncated).toBe(true);
    expect(w.shown).toHaveLength(5);
    expect(w.total).toBe(12);
  });
  it("does not disclose when the feed exactly fills the cap", () => {
    const w = changeWindow(items.slice(0, 5), 5);
    expect(w.truncated).toBe(false);
    expect(w.total).toBe(5);
  });
});
