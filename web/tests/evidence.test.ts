import { describe, expect, it } from "vitest";
import {
  applyEvidence,
  buildHistory,
  emptySurfaceEvidence,
  isUnknownValue,
  leadingClaim,
  valueDisplay,
  type EvidenceClaim,
  type SurfaceEvidence,
} from "../lib/evidence";
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
    evidenceStatus: "no_evidence",
    evidenceLabel: "No evidence",
    evidenceNote: "none",
    confidenceLabel: "Unknown — no validated claim",
    freshnessLabel: "No capture yet",
    evidenceClaimCount: 0,
    lastReviewed: "2026-09-01",
    searchHaystack: "widget search",
  };
}

function claim(overrides: Partial<EvidenceClaim> = {}): EvidenceClaim {
  return {
    claim_id: "c1",
    topic: "audience_usage",
    statement: "Widget Search had 1.2M monthly visits.",
    confidence: "medium",
    confidence_detail: { score: 0.62, inputs: { recency: 0.7 }, rationale: ["Derived from recency+source_class."], derived: true },
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
    provenance: [
      {
        field_path: "metrics[0].value",
        locator_kind: "verbatim_quote",
        quote: "1.2 million monthly visits",
        selector: "#stats",
      },
    ],
    evidence: [{ capture_hash: "abc123", snapshot_available: true, fetched_at: "2026-09-16T00:00:00Z" }],
    freshness: { state: "recent", age_days: 3, observed_at: "2026-09-16T00:00:00Z" },
    ...overrides,
  };
}

function surface(claims: EvidenceClaim[], extra: Partial<SurfaceEvidence> = {}): SurfaceEvidence {
  return {
    surface: "widget-search",
    evidence_state: claims.length ? "evidenced" : "no_evidence",
    evidence_note: claims.length ? null : "No validated claim is linked to this surface yet.",
    claims,
    latest_change: null,
    ...extra,
  };
}

describe("value projection", () => {
  it("marks a null/number-null value as Unknown, never blank", () => {
    const unknown = claim().value[0];
    expect(isUnknownValue({ ...unknown, value_number: null, value_text: null })).toBe(true);
    expect(valueDisplay({ ...unknown, value_number: null, value_text: null })).toBe("Unknown");
    expect(valueDisplay(unknown)).toBe("1.2M");
  });
});

describe("evidence projection (issue #46)", () => {
  it("reports ALL claims on the summary row, never claims[0] only", () => {
    const second = claim({ claim_id: "c2", statement: "Widget Search crawler honours robots.txt.", topic: "crawler_policy" });
    const [out] = applyEvidence([row("widget-search")], { "widget-search": surface([claim(), second]) });

    // The row is a lightweight summary: the count reflects every claim, and the
    // full payload is no longer embedded on the client row (loaded lazily).
    expect(out.evidenceClaimCount).toBe(2);
    expect(out.evidenceNote).toContain("2 validated claims");
    expect((out as unknown as { evidence?: unknown }).evidence).toBeUndefined();
  });

  it("keeps provenance and source available on the claim for the lazily-loaded detail", () => {
    const ev = surface([claim()]);
    expect(ev.claims[0].provenance[0].quote).toBe("1.2 million monthly visits");
    expect(ev.claims[0].provenance[0].locator_kind).toBe("verbatim_quote");
    expect(ev.claims[0].source.url).toBe("https://example.test");
    expect(ev.claims[0].source.source_class).toBe("official");
  });

  it("reports an explicit no-evidence state for a surface with no claim", () => {
    const [out] = applyEvidence([row("no-such-surface")], {});
    expect(out.evidenceStatus).toBe("no_evidence");
    expect(out.evidenceClaimCount).toBe(0);
    expect(out.evidenceLabel).toBe("No evidence");
    expect(out.evidenceNote).toMatch(/no validated claim/i);
  });

  it("surfaces an unknown-only claim without inventing a value", () => {
    const unknownClaim = claim({ value: [{ ...claim().value[0], value_number: null, value_text: null, known: false }] });
    const [out] = applyEvidence([row("widget-search")], { "widget-search": surface([unknownClaim]) });
    expect(out.evidenceStatus).toBe("evidenced");
    // Only the count is stated; no fabricated value leaks into the summary.
    expect(out.evidenceNote).toContain("no known values");
    expect(out.evidenceNote).not.toContain("1.2M");
  });

  it("chooses the highest-confidence claim as the leading summary", () => {
    const low = claim({ claim_id: "low", confidence_detail: { ...claim().confidence_detail, score: 0.2 } });
    const high = claim({ claim_id: "high", confidence_detail: { ...claim().confidence_detail, score: 0.9 } });
    expect(leadingClaim([low, high])!.claim_id).toBe("high");
  });
});

describe("chronological history", () => {
  it("merges claims and events newest-first and links an event to its claim", () => {
    const claimOne = claim();
    const history = buildHistory(
      [claimOne],
      [
        {
          id: "ev1",
          event_type: "crawler_policy",
          title: "Robots policy updated",
          source_hash: "abc123", // matches claimOne.evidence[0].capture_hash
          observed_at: "2026-09-18T00:00:00Z",
          evidence_urls: ["https://example.test/bots"],
        },
      ],
    );
    expect(history).toHaveLength(1);
    expect(history[0].kind).toBe("change");
    expect(history[0].claimId).toBe("c1");
    expect(history[0].date).toBe("2026-09-18T00:00:00Z");
  });

  it("keeps an unlinked claim in the history", () => {
    const history = buildHistory([claim()], []);
    expect(history).toHaveLength(1);
    expect(history[0].kind).toBe("claim");
    expect(history[0].title).toContain("1.2M");
  });
});
