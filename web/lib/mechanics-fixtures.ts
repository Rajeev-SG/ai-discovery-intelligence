/**
 * Recorded-fixture mode (EVIDENCE_FIXTURE=1) for the evidence & trust layer
 * (issue #58). Static, recorded data only — never used in production. Mirrors the
 * real `/surfaces/{id}/mechanics` payload shape so the trust layer can be tested
 * structurally in CI without a live backend, including a vendor-documented case,
 * an independently-researched case, a controlled observation, and an inline
 * conflict — the four cases issue #58's product proof requires.
 */
import type { MechanicsDimension, SurfaceMechanics } from "./mechanics";

function dimension(partial: Partial<MechanicsDimension> & { dimension: string }): MechanicsDimension {
  return {
    label: partial.dimension,
    definition: "",
    state: "unknown",
    note: "No validated claim for this surface covers this dimension.",
    assertions: [],
    ...partial,
  };
}

const ALL = [
  "search_trigger",
  "retrieval_provider",
  "query_rewrite",
  "crawling_indexing_controls",
  "freshness_recrawl",
  "candidate_selection_reranking",
  "citation_presentation",
  "shopping_product_feed",
  "local_retrieval",
  "social_community_retrieval",
  "mode_region_differences",
  "answer_type",
  "marketer_controllable_inputs",
];

const CHATGPT: SurfaceMechanics = {
  surface: "chatgpt",
  evidenced_dimension_count: 3,
  dimension_count: 13,
  coverage: { known: 3, partially_known: 0, conflicting: 1, unknown: 6 },
  dimensions: ALL.map((name) => {
    if (name === "crawling_indexing_controls") {
      return dimension({
        dimension: name,
        label: "Crawling and indexing controls",
        state: "known",
        assertions: [
          {
            statement: "Adjusting for a robots.txt update can take about a day.",
            state: "known",
            conflict_note: null,
            evidence: [
              {
                claim_id: "fx-crawler-1",
                source_id: "openai-bots",
                publisher: "OpenAI",
                url: "https://developers.openai.com/api/docs/bots",
                source_class: "official",
                evidence_class: "official_documentation",
                published_at: "2026-09-01",
                observed_at: "2026-09-19T00:00:00Z",
                effective_from: null,
                confidence: "medium",
                confidence_score: 0.62,
                confidence_rationale: ["source_authority: 1.00 (official)"],
                freshness_state: "fresh",
                freshness_age_days: 1,
                measurement_mode: "official_documentation",
                methodology_notes: "Vendor crawler documentation.",
                methodology_completeness: "sparse",
                limitations: [],
                modes: [],
                regions: [],
                relates_to_claim_id: null,
                relationship: "new",
                reconciliation: [],
              },
            ],
          },
        ],
      });
    }
    if (name === "citation_presentation") {
      return dimension({
        dimension: name,
        label: "Citation / source presentation",
        state: "conflicting",
        assertions: [
          {
            statement: "The share of responses with inline links rose to 35%.",
            state: "conflicting",
            conflict_note: "Evidence for this dimension disagrees across sources; both are preserved.",
            evidence: [
              {
                claim_id: "fx-inline-2",
                source_id: "sistrix",
                publisher: "SISTRIX",
                url: "https://www.sistrix.com/feed/",
                source_class: "visibility_research",
                evidence_class: "independent_research",
                published_at: null,
                observed_at: "2026-09-17T00:00:00Z",
                effective_from: null,
                confidence: "low",
                confidence_score: 0.31,
                confidence_rationale: ["sample_strength: no sample size stated"],
                freshness_state: "recent",
                freshness_age_days: 2,
                measurement_mode: "visibility_panel",
                methodology_notes: "Panel of tracked prompts.",
                methodology_completeness: "sparse",
                limitations: [],
                modes: [],
                regions: [],
                relates_to_claim_id: null,
                relationship: "new",
                reconciliation: [
                  {
                    claim_ids: ["fx-inline-2", "fx-inline-3"],
                    state: "material_conflict",
                    relationship: "contradicts",
                    confidence_adjustment: -0.2,
                    differences: ["value"],
                    unknown_dimensions: [],
                    interpretation: "The two readings disagree on the share of responses with inline links.",
                  },
                ],
              },
              {
                claim_id: "fx-observed-3",
                source_id: "our-observation",
                publisher: "Controlled observation (issue #10 lane)",
                url: null,
                source_class: "controlled_observation",
                evidence_class: "controlled_observation",
                published_at: null,
                observed_at: "2026-09-18T00:00:00Z",
                effective_from: null,
                confidence: "low",
                confidence_score: 0.4,
                confidence_rationale: ["sample_strength: no sample size stated"],
                freshness_state: "fresh",
                freshness_age_days: 0,
                measurement_mode: "controlled_observation",
                methodology_notes: "Directly observed on the consumer surface.",
                methodology_completeness: "sparse",
                limitations: ["Narrow sample."],
                modes: ["web"],
                regions: ["us"],
                relates_to_claim_id: null,
                relationship: "new",
                reconciliation: [],
              },
            ],
          },
        ],
      });
    }
    return dimension({ dimension: name });
  }),
};

export function fixtureMechanics(surfaceId: string): SurfaceMechanics | null {
  if (surfaceId === "chatgpt") return CHATGPT;
  return null;
}
