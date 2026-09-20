import { describe, expect, it } from "vitest";
import {
  MECHANICS_STATE_LABELS,
  dimensionEvidenceClass,
  evidenceClassLabel,
  evidencedDimensions,
  type MechanicsEvidence,
  type SurfaceMechanics,
} from "../lib/mechanics";
import { RETRIEVAL_UNKNOWNS_SOURCE, retrievalUnknowns } from "../lib/surfaces";

function surface(partial: Partial<SurfaceMechanics>): SurfaceMechanics {
  return {
    surface: "chatgpt",
    dimensions: [],
    coverage: { known: 0, partially_known: 0, conflicting: 0, unknown: 0 },
    evidenced_dimension_count: 0,
    dimension_count: 13,
    ...partial,
  };
}

describe("mechanics contract helpers", () => {
  it("labels every mechanics state", () => {
    for (const state of ["known", "partially_known", "conflicting", "unknown"] as const) {
      expect(MECHANICS_STATE_LABELS[state]).toBeTruthy();
    }
  });

  it("keeps the three evidence classes distinct and labelled", () => {
    expect(evidenceClassLabel("official_documentation")).toMatch(/document/i);
    expect(evidenceClassLabel("independent_research")).toMatch(/independent/i);
    expect(evidenceClassLabel("controlled_observation")).toMatch(/observed/i);
  });

  it("never renders an unknown dimension as evidenced", () => {
    const s = surface({
      dimensions: [
        { dimension: "answer_type", label: "Answer type", definition: "", state: "unknown", note: "n", assertions: [] },
        {
          dimension: "citation_presentation",
          label: "Citations",
          definition: "",
          state: "known",
          note: "",
          assertions: [],
        },
      ],
    });
    const shown = evidencedDimensions(s).map((d) => d.dimension);
    expect(shown).toEqual(["citation_presentation"]);
  });

  it("prefers official documentation when a dimension mixes evidence classes", () => {
    const dim = {
      dimension: "crawling_indexing_controls",
      label: "Crawling",
      definition: "",
      state: "known" as const,
      note: "",
      assertions: [
        {
          statement: "x",
          state: "known" as const,
          conflict_note: null,
          evidence: [
            { evidence_class: "independent_research" },
            { evidence_class: "official_documentation" },
          ].map((e, i) => ({
            claim_id: `c${i}`,
            source_id: null,
            publisher: null,
            url: null,
            source_class: "official",
            evidence_class: e.evidence_class,
            published_at: null,
            observed_at: null,
            effective_from: null,
            confidence: "high",
            confidence_score: null,
            confidence_rationale: [],
            freshness_state: "unknown",
            freshness_age_days: null,
            measurement_mode: null,
            methodology_notes: null,
            limitations: [],
            modes: [],
            regions: [],
            relates_to_claim_id: null,
            relationship: "new",
          })),
        },
      ],
    };
    expect(dimensionEvidenceClass(dim)).toBe("official_documentation");
  });

  it("treats registry retrieval-unknowns as registry metadata, not evidence", () => {
    expect(RETRIEVAL_UNKNOWNS_SOURCE).toBe("registry_metadata");
    expect(retrievalUnknowns("under_documented").length).toBeGreaterThan(0);
  });
});

describe("evidence & trust helpers (issue #58)", () => {
  const ev = (over: Partial<MechanicsEvidence> = {}): MechanicsEvidence => ({
    claim_id: "c1",
    source_id: null,
    publisher: "OpenAI",
    url: "https://platform.openai.com/docs/bots",
    source_class: "official",
    evidence_class: "official_documentation",
    published_at: "2026-09-01",
    observed_at: "2026-09-19T00:00:00Z",
    effective_from: null,
    confidence: "high",
    confidence_score: 0.9,
    confidence_rationale: ["source_authority: 1.00 (official)"],
    freshness_state: "fresh",
    freshness_age_days: 1,
    measurement_mode: "official_documentation",
    methodology_notes: "Vendor docs",
    limitations: [],
    modes: [],
    regions: [],
    relates_to_claim_id: null,
    relationship: "new",
    reconciliation: [],
    ...over,
  });

  it("keeps the three classes distinct and labelled", () => {
    expect(evidenceClassLabel("official_documentation")).toBe("Vendor-documented");
    expect(evidenceClassLabel("independent_research")).toBe("Independently researched");
    expect(evidenceClassLabel("controlled_observation")).toBe("Directly observed");
  });

  it("reports no-evidence for a surface whose dimensions are all unknown", () => {
    const s = surface({ dimensions: [] });
    expect(s.evidenced_dimension_count).toBe(0);
    expect(evidencedDimensions(s)).toEqual([]);
  });

  it("carries inline reconciliation records verbatim from the backend", () => {
    const withConflict = ev({
      reconciliation: [
        {
          claim_ids: ["c1", "c2"],
          state: "material_conflict",
          relationship: "contradicts",
          confidence_adjustment: -0.2,
          differences: ["value"],
          unknown_dimensions: [],
          interpretation: "The two readings disagree.",
        },
      ],
    });
    expect(withConflict.reconciliation?.[0].state).toBe("material_conflict");
    expect(withConflict.reconciliation?.[0].relationship).toBe("contradicts");
  });

  it("distinguishes official documentation from controlled observation", () => {
    const observed = ev({ source_class: "controlled_observation", evidence_class: "controlled_observation" });
    expect(evidenceClassLabel(observed.evidence_class)).not.toBe(
      evidenceClassLabel(ev().evidence_class),
    );
  });

  it("represents unknown freshness explicitly rather than guessing", () => {
    const unknownFresh = ev({ freshness_state: "unknown", freshness_age_days: null });
    expect(unknownFresh.freshness_state).toBe("unknown");
    expect(unknownFresh.freshness_age_days).toBeNull();
  });
});
