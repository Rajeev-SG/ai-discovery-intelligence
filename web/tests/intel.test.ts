import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { fetchBrief, fetchEvents } from "../lib/intel";

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
