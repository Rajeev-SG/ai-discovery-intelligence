/**
 * Recorded-fixture mode (EVIDENCE_FIXTURE=1) for the marketing implications view
 * (issue #59). Static, recorded data only — never used in production. Mirrors the
 * real `/implications` payload shape so the view can be tested structurally in CI
 * without a live backend, including a cross-surface implication and an explicit
 * monitor-only surface.
 */
import type { Implication, ImplicationsProjection } from "./implications";

const CRAWL: Implication = {
  family: "crawlability_eligibility",
  action:
    "Confirm the crawler user-agents named in the vendor documentation are allowed in robots.txt, and that any disallow is deliberate.",
  rationale:
    "The surface's crawler controls are vendor-documented, so eligibility is a decision you control.",
  supporting_claim_ids: ["fx-crawler-1"],
  supporting_dimensions: ["crawling_indexing_controls"],
  surfaces: ["chatgpt", "claude"],
  modes: [],
  regions: [],
  confidence: "medium",
  actionability: "high",
  significance: 3.63,
  contradicting_claim_ids: [],
  monitor_only: false,
  note: "Applies across 2 surfaces that share this evidenced mechanic.",
};

const CITATION: Implication = {
  family: "citation_visibility",
  action:
    "Treat citations as a first-class outcome: track which pages are cited and structure content to be quotable.",
  rationale:
    "The surface's citation presentation is evidenced, so source visibility is a measurable outcome.",
  supporting_claim_ids: ["fx-inline-2"],
  supporting_dimensions: ["citation_presentation"],
  surfaces: ["chatgpt"],
  modes: [],
  regions: [],
  confidence: "low",
  actionability: "medium",
  significance: 3.1,
  contradicting_claim_ids: ["fx-inline-3"],
  monitor_only: false,
  note: "",
};

export function fixtureImplications(): ImplicationsProjection {
  return {
    count: 2,
    surfaces: {
      chatgpt: {
        surface: "chatgpt",
        monitor_only: false,
        note: "",
        implications: [CRAWL, CITATION],
      },
      grok: {
        surface: "grok",
        monitor_only: true,
        note: "No evidenced, marketer-actionable mechanic for this surface yet. Monitor rather than act: unknown is a valid answer.",
        implications: [],
      },
    },
    cross_surface: [CRAWL, CITATION],
  };
}
