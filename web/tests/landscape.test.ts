import { describe, expect, it } from "vitest";
import {
  coverageLabel,
  parseComparisonIds,
  unknownCellCount,
  COMPARISON_MAX,
  type LandscapeSurface,
  type LandscapeProjection,
} from "../lib/landscape";

function surface(over: Partial<LandscapeSurface> = {}): LandscapeSurface {
  return {
    id: "chatgpt",
    name: "ChatGPT",
    vendor: "OpenAI",
    type: "conversational_assistant",
    type_label: "Conversational assistant",
    priority: "Core — global",
    regions: ["global"],
    discovery_modes: ["web_search"],
    official_url: "https://chatgpt.com/",
    reach_metric: "market share: 79.4 percent",
    reach_claim_id: "c1",
    reach_confidence: "medium",
    evidenced_dimensions: 7,
    dimension_count: 13,
    coverage: { known: 7, partially_known: 0, conflicting: 0, unknown: 6 },
    relevance: "sources are cited",
    ...over,
  };
}

describe("landscape helpers (issue #60)", () => {
  it("formats coverage as evidenced/total", () => {
    expect(coverageLabel(surface())).toBe("7/13 evidenced");
  });

  it("parses and caps a comma-separated comparison id list", () => {
    expect(parseComparisonIds("chatgpt, claude ,chatgpt")).toEqual(["chatgpt", "claude"]);
    const many = parseComparisonIds("a,b,c,d,e,f,g,h");
    expect(many.length).toBe(COMPARISON_MAX);
  });

  it("returns [] for an empty selection param", () => {
    expect(parseComparisonIds(null)).toEqual([]);
    expect(parseComparisonIds("")).toEqual([]);
  });

  it("counts unknown cells per surface, keeping them explicit", () => {
    const projection: LandscapeProjection = {
      surfaces: [surface()],
      comparison_surface_ids: ["chatgpt"],
      comparison: [
        {
          dimension: "citation_presentation",
          label: "Citations",
          definition: "",
          cells: {
            chatgpt: {
              dimension: "citation_presentation",
              state: "unknown",
              statement: null,
              claim_id: null,
              evidence_class: null,
              confidence: null,
              unknown: true,
            },
          },
        },
        {
          dimension: "crawling_indexing_controls",
          label: "Crawling",
          definition: "",
          cells: {
            chatgpt: {
              dimension: "crawling_indexing_controls",
              state: "known",
              statement: "x",
              claim_id: "c1",
              evidence_class: "official_documentation",
              confidence: "high",
              unknown: false,
            },
          },
        },
      ],
    };
    expect(unknownCellCount(projection, "chatgpt")).toBe(1);
  });
});
