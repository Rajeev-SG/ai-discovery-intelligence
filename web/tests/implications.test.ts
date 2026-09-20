import { describe, expect, it } from "vitest";
import {
  actionabilityLabel,
  familyLabel,
  rankedImplications,
  actionableSurfaces,
  type ImplicationsProjection,
} from "../lib/implications";

function projection(): ImplicationsProjection {
  return {
    count: 2,
    surfaces: {
      chatgpt: {
        surface: "chatgpt",
        monitor_only: false,
        note: "",
        implications: [
          {
            family: "crawlability_eligibility",
            action: "Check robots.txt",
            rationale: "documented control",
            supporting_claim_ids: ["c1"],
            supporting_dimensions: ["crawling_indexing_controls"],
            surfaces: ["chatgpt"],
            modes: [],
            regions: [],
            confidence: "high",
            actionability: "high",
            significance: 3.6,
            contradicting_claim_ids: [],
            monitor_only: false,
            note: "",
          },
        ],
      },
      grok: { surface: "grok", monitor_only: true, note: "watch", implications: [] },
    },
    cross_surface: [
      {
        family: "citation_visibility",
        action: "Track citations",
        rationale: "measured outcome",
        supporting_claim_ids: ["c2"],
        supporting_dimensions: ["citation_presentation"],
        surfaces: ["chatgpt"],
        modes: [],
        regions: [],
        confidence: "low",
        actionability: "medium",
        significance: 3.1,
        contradicting_claim_ids: [],
        monitor_only: false,
        note: "",
      },
      {
        family: "crawlability_eligibility",
        action: "Check robots.txt",
        rationale: "documented control",
        supporting_claim_ids: ["c1"],
        supporting_dimensions: ["crawling_indexing_controls"],
        surfaces: ["chatgpt"],
        modes: [],
        regions: [],
        confidence: "high",
        actionability: "high",
        significance: 3.6,
        contradicting_claim_ids: [],
        monitor_only: false,
        note: "",
      },
    ],
  };
}

describe("implications helpers (issue #59)", () => {
  it("labels every family and actionability value", () => {
    for (const f of [
      "crawlability_eligibility",
      "citation_visibility",
      "monitor",
    ] as const) {
      expect(familyLabel(f)).toBeTruthy();
    }
    expect(actionabilityLabel("high")).toMatch(/actionable/i);
    expect(actionabilityLabel("low")).toMatch(/informational/i);
  });

  it("ranks implications by actionability then significance", () => {
    const ranked = rankedImplications(projection());
    expect(ranked[0].actionability).toBe("high");
    expect(ranked[0].significance).toBeGreaterThanOrEqual(ranked[1].significance);
  });

  it("never lists a monitor-only surface as actionable", () => {
    const actionable = actionableSurfaces(projection());
    expect(actionable.map((s) => s.surface)).toEqual(["chatgpt"]);
  });
});
