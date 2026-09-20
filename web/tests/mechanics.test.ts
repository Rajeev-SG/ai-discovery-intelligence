import { describe, expect, it } from "vitest";
import {
  MECHANICS_STATE_LABELS,
  dimensionEvidenceClass,
  evidenceClassLabel,
  evidencedDimensions,
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
