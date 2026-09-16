import { describe, expect, it } from "vitest";
import { loadRegistry } from "../lib/registry";
import {
  RETRIEVAL_STATUS_LABELS,
  retrievalUnknowns,
  toSurfaceRows,
  type SurfaceRow,
} from "../lib/surfaces";
import { decodeUrlState, encodeUrlState } from "../lib/url-state";

const registry = loadRegistry();
const rows = toSurfaceRows(registry);

function find(id: string): SurfaceRow {
  const row = rows.find((candidate) => candidate.id === id);
  if (!row) throw new Error(`missing row ${id}`);
  return row;
}

describe("canonical registry", () => {
  it("renders every surface in config/surfaces.yaml", () => {
    expect(rows.length).toBe(registry.surfaces.length);
    expect(rows.length).toBe(35);
    const ids = new Set(rows.map((row) => row.id));
    expect(ids.size).toBe(35);
  });

  it("includes the global and regional surfaces the issue names", () => {
    for (const id of ["chatgpt", "deepseek-chat", "doubao", "qwen-consumer", "naver-ai", "yandex-ai-search"]) {
      expect(find(id).name.length).toBeGreaterThan(0);
    }
  });

  it("keeps registry facts verbatim", () => {
    const deepseek = find("deepseek-chat");
    expect(deepseek.vendor).toBe("DeepSeek");
    expect(deepseek.family).toBe("DeepSeek");
    expect(deepseek.retrievalStatus).toBe("under_documented");
    expect(deepseek.regions).toEqual(["global", "china"]);
    expect(deepseek.officialUrls).toContain("https://chat.deepseek.com/");
    expect(deepseek.officialUrls).toContain("https://api-docs.deepseek.com/");
  });

  it("labels every row with a known retrieval status", () => {
    for (const row of rows) {
      expect(RETRIEVAL_STATUS_LABELS[row.retrievalStatus]).toBe(row.retrievalStatusLabel);
    }
  });

  it("never invents evidence for issue 01", () => {
    for (const row of rows) {
      expect(row.evidenceStatus).toBe("not_yet_ingested");
      expect(row.confidenceLabel).toBe("Not yet assessed");
      expect(row.evidenceNote).toMatch(/ingested/i);
      // No fabricated figures: the registry surface row carries no metrics.
      for (const field of [row.evidenceLabel, row.confidenceLabel, row.freshnessLabel]) {
        expect(field).not.toMatch(/[%≈]/);
      }
    }
  });

  it("states explicit unknowns instead of empty cells", () => {
    for (const row of rows) {
      expect(row.retrievalUnknownNotes.length).toBeGreaterThan(0);
    }
    const chinaChina = find("doubao");
    expect(chinaChina.retrievalUnknown).toBe(true);
    expect(find("chatgpt").retrievalUnknown).toBe(false);
    expect(retrievalUnknowns("under_documented")[0]).toMatch(/not documented/i);
  });
});

describe("search fields", () => {
  it("searches regions so a China query matches every China surface", () => {
    const haystacks = rows.filter((row) => row.searchHaystack.includes("china")).map((row) => row.id);
    for (const id of ["doubao", "qwen-consumer", "quark-ai", "kimi", "baidu-ai-search", "deepseek-chat"]) {
      expect(haystacks).toContain(id);
    }
    expect(haystacks.length).toBeGreaterThanOrEqual(9);
  });

  it("searches vendor, family and retrieval status", () => {
    expect(rows.filter((r) => r.searchHaystack.includes("bytedance")).map((r) => r.id)).toEqual(["doubao"]);
    expect(rows.filter((r) => r.searchHaystack.includes("naver")).map((r) => r.id)).toEqual(["naver-ai"]);
    expect(rows.some((r) => r.searchHaystack.includes("under-documented"))).toBe(true);
  });
});

describe("commercial priority", () => {
  it("ranks core surfaces ahead of watchlist surfaces", () => {
    expect(find("chatgpt").priorityRank).toBeLessThan(find("poe").priorityRank);
    expect(find("doubao").priorityRank).toBeLessThan(find("manus").priorityRank);
  });
});

describe("URL state", () => {
  it("round-trips search, sort, filters, expansion and columns", () => {
    const state = {
      q: "China",
      sort: [{ id: "name", desc: true }],
      filters: { regions: ["china"], retrieval: ["Under-documented"] },
      expanded: ["deepseek-chat"],
      cols: ["name", "regions"],
    };
    const encoded = encodeUrlState(state);
    const decoded = decodeUrlState(new URLSearchParams(encoded));
    expect(decoded.q).toBe("China");
    expect(decoded.sort).toEqual(state.sort);
    expect(decoded.filters).toEqual(state.filters);
    expect(decoded.expanded).toEqual(["deepseek-chat"]);
    expect(decoded.cols).toEqual(state.cols);
  });

  it("encodes nothing when pristine", () => {
    expect(encodeUrlState({ q: "", sort: [], filters: {}, expanded: [], cols: [] })).toBe("");
  });
});
