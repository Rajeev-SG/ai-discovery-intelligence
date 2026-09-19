import { describe, expect, it } from "vitest";
import { applyEvidence, emptySurfaceEvidence, type SurfaceEvidence } from "../lib/evidence";
import type { SurfaceRow } from "../lib/surfaces";

function row(id: string): SurfaceRow {
  return {
    id,
    name: "Widget Search",
    vendor: "Widget",
    family: "search_augmentation",
    type: "ai_native_search",
    typeLabel: "AI-native search",
    tier: "core_global",
    tierLabel: "Core — global",
    priorityRank: 1,
    regions: ["global"],
    regionLabels: ["Global"],
    distribution: [],
    distributionLabels: [],
    discoveryModes: [],
    discoveryModeLabels: [],
    retrievalStatus: "documented",
    retrievalStatusLabel: "Documented",
    retrievalUnknown: false,
    retrievalUnknownNotes: [],
    officialUrls: [],
    evidenceStatus: "not_yet_ingested",
    evidenceLabel: "Not yet ingested",
    evidenceNote: "placeholder",
    confidenceLabel: "Not yet assessed",
    freshnessLabel: "Registry reviewed 2026-09-01",
    lastReviewed: "2026-09-01",
    searchHaystack: "widget search",
  };
}

const evidenced: SurfaceEvidence = {
  surface: "widget-search",
  evidence_state: "evidenced",
  evidence_note: null,
  claims: [
    {
      claim_id: "c1",
      topic: "audience_usage",
      statement: "Widget Search had 1.2M monthly visits.",
      confidence: "medium",
      confidence_detail: { score: 0.62, inputs: { recency: 0.7 }, rationale: [], derived: true },
      value: [
        {
          metric_id: "visits",
          label: "Monthly visits",
          value_number: 1200000,
          value_text: "1.2M",
          unit: "visits",
          window: "Jan 2026",
          scope: "Widget Search",
          known: true,
        },
      ],
      source: { publisher: "Widget Inc", url: "https://example.test", source_class: "official" },
      provenance: [],
      evidence: [{ capture_hash: "abc", snapshot_available: true, fetched_at: "2026-09-16T00:00:00Z" }],
      freshness: { state: "recent", age_days: 3, observed_at: "2026-09-16T00:00:00Z" },
    },
  ],
  latest_change: null,
};

describe("evidence projection", () => {
  it("projects a real claim value, derived confidence and freshness", () => {
    const [out] = applyEvidence([row("widget-search")], { "widget-search": evidenced });
    expect(out.evidenceStatus).toBe("evidenced");
    expect(out.evidenceNote).toContain("1.2M");
    expect(out.confidenceLabel).toContain("medium");
    expect(out.freshnessLabel).toContain("Recent");
  });

  it("renders an explicit no-evidence state for a surface with no claim", () => {
    const [out] = applyEvidence([row("no-such-surface")], {});
    expect(out.evidenceStatus).toBe("no_evidence");
    expect(out.evidenceLabel).toBe("No evidence");
    expect(out.confidenceLabel).toContain("Unknown");
    expect(out.evidenceNote).not.toContain("placeholder");
  });

  it("never invents a value for a claim with only unknown metrics", () => {
    const unknownClaim: SurfaceEvidence = {
      ...evidenced,
      claims: [
        {
          ...evidenced.claims[0],
          value: [{ ...evidenced.claims[0].value[0], value_number: null, value_text: null, known: false }],
        },
      ],
    };
    const [out] = applyEvidence([row("widget-search")], { "widget-search": unknownClaim });
    expect(out.evidenceNote).toContain("Unknown value");
  });

  it("emptySurfaceEvidence is explicitly no-evidence", () => {
    expect(emptySurfaceEvidence("x").evidence_state).toBe("no_evidence");
  });
});
