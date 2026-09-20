/**
 * Recorded-fixture mode (EVIDENCE_FIXTURE=1) for structural tests/CI without
 * the live API. Static, recorded data only — never used in production. Keeps
 * the contract-faithful shape of the real `/surface-evidence` and
 * `/surfaces/{id}/evidence` payloads so the drawer can be tested structurally.
 */
import type { EvidenceClaim, EvidenceEvent, SurfaceDetail, SurfaceEvidence } from "@/lib/evidence";

const CHATGPT_CLAIMS: EvidenceClaim[] = [
  {
    claim_id: "fx-crawler-1",
    topic: "crawler_index_policy",
    statement: "Adjusting for a robots.txt update can take about a day.",
    confidence: "medium",
    confidence_detail: {
      score: 0.62,
      inputs: { recency: 0.9, source_class: 1 },
      rationale: ["Derived from recency and official-source class."],
      derived: true,
    },
    value: [
      {
        metric_id: "m1",
        label: "Time to adjust after robots.txt update",
        value_number: null,
        value_text: "~24 hours",
        unit: "",
        window: "rolling",
        scope: "search results",
        known: true,
      },
      {
        metric_id: "m2",
        label: "Disclosed adjustment SLA",
        value_number: null,
        value_text: null,
        unit: null,
        window: null,
        scope: null,
        known: false,
      },
    ],
    source: { publisher: "OpenAI", url: "https://developers.openai.com/api/docs/bots", source_class: "official" },
    provenance: [
      {
        field_path: "metrics[0].value",
        locator_kind: "verbatim_quote",
        quote: "it can take ~24 hours from a site's robots.txt update for our systems to adjust",
        selector: null,
      },
    ],
    evidence: [{ capture_hash: "fixture-capture-hash-1", snapshot_available: true, fetched_at: "2026-09-19T00:00:00Z" }],
    freshness: { state: "fresh", age_days: 0, observed_at: "2026-09-19T16:00:00Z" },
  },
  {
    claim_id: "fx-inline-2",
    topic: "citation_presentation",
    statement: "A share of responses carries inline link elements.",
    confidence: "low",
    confidence_detail: { score: 0.31, inputs: { sample_size: 0.4 }, rationale: [], derived: true },
    value: [
      {
        metric_id: "m3",
        label: "Share of responses with inline links",
        value_number: 35,
        value_text: null,
        unit: "%",
        window: "after 2026-07-11",
        scope: "ChatGPT responses",
        known: true,
      },
    ],
    source: { publisher: "SISTRIX", url: "https://www.sistrix.com/feed/", source_class: "visibility_research" },
    provenance: [],
    evidence: [{ capture_hash: "fixture-capture-hash-2", snapshot_available: false, fetched_at: "2026-09-19T00:00:00Z" }],
    freshness: { state: "recent", age_days: 2, observed_at: "2026-09-17T00:00:00Z" },
  },
];

const CHATGPT_EVENTS: EvidenceEvent[] = [
  {
    id: "fx-event-1",
    event_type: "crawler_policy",
    title: "Adjusting for a robots.txt update can take about a day.",
    source_hash: "fixture-capture-hash-1",
    observed_at: "2026-09-19T16:00:00Z",
    evidence_urls: ["https://developers.openai.com/api/docs/bots"],
  },
];

export function fixtureSurfaces(): Record<string, SurfaceEvidence> {
  return {
    chatgpt: {
      surface: "chatgpt",
      evidence_state: "evidenced",
      evidence_note: null,
      claims: CHATGPT_CLAIMS,
      latest_change: {
        id: "fx-event-1",
        event_type: "crawler_policy",
        title: "Adjusting for a robots.txt update can take about a day.",
        published_at: null,
        observed_at: "2026-09-19T16:00:00Z",
      },
      history: [],
    },
    grok: {
      surface: "grok",
      evidence_state: "no_evidence",
      evidence_note: "No validated claim is linked to this surface yet.",
      claims: [],
      latest_change: null,
      history: [],
    },
  };
}

export function fixtureDetail(surfaceId: string): SurfaceDetail {
  const surfaces = fixtureSurfaces();
  const evidence = surfaces[surfaceId] ?? {
    surface: surfaceId,
    evidence_state: "no_evidence" as const,
    evidence_note: "No validated claim is linked to this surface yet.",
    claims: [],
    latest_change: null,
    history: [],
  };
  return {
    evidence: { ...evidence, history: surfaceId === "chatgpt" ? CHATGPT_EVENTS : [] },
    status: { evidence: "ok", claims: "ok", events: "ok" },
  };
}
