import { describe, expect, it } from "vitest";
import {
  CONFIDENCE_LABELS,
  evidenceHref,
  formatDate,
  formatDateTime,
  hasChanges,
  isContested,
  isUnresolved,
  loadPov,
  projectPov,
} from "../lib/pov";

// A minimal valid proposition builder so each test states only what it asserts.
function prop(overrides: Record<string, unknown> = {}) {
  return {
    id: "pov-test",
    section: "Test section",
    base_text: "Base position.",
    topics: ["measurement"],
    confidence: "unresolved",
    contested: false,
    last_reviewed: null,
    supporting: [],
    contradicting: [],
    ...overrides,
  };
}

describe("canonical POV artifact", () => {
  const view = loadPov();

  it("projects all four canonical propositions", () => {
    expect(view.propositions.map((p) => p.id)).toEqual([
      "pov-retrieval-systems",
      "pov-channel-prioritisation",
      "pov-commerce-ads",
      "pov-measurement",
    ]);
  });

  it("renders pov-retrieval-systems as medium with one supporting item and its real change", () => {
    const retrieval = view.propositions.find((p) => p.id === "pov-retrieval-systems");
    if (!retrieval) throw new Error("missing retrieval proposition");
    expect(retrieval.confidence).toBe("medium");
    expect(retrieval.supporting).toHaveLength(1);
    expect(retrieval.contradicting).toHaveLength(0);
    expect(retrieval.supporting[0].claim_id).toBe("0b187a5b6f942c1d2a3fcb12285238e5");
    expect(retrieval.last_reviewed).not.toBeNull();

    const change = view.changelog.find((c) => c.proposition_id === "pov-retrieval-systems");
    if (!change) throw new Error("missing retrieval changelog entry");
    expect(change.changed_at.startsWith("2026-09-19")).toBe(true);
    expect(change.evidence_ids).toContain("0b187a5b6f942c1d2a3fcb12285238e5");
    expect(change.significance).toBeGreaterThanOrEqual(3.5);
    expect(change.confidence).toBe("medium");
  });

  it("renders at least one proposition as unresolved", () => {
    const unresolved = view.propositions.filter(isUnresolved);
    expect(unresolved.map((p) => p.id)).toContain("pov-channel-prioritisation");
    const channel = view.propositions.find((p) => p.id === "pov-channel-prioritisation");
    if (!channel) throw new Error("missing channel proposition");
    expect(channel.confidence).toBe("unresolved");
    expect(channel.supporting).toHaveLength(0);
    expect(channel.contradicting).toHaveLength(0);
    expect(channel.last_reviewed).toBeNull();
  });
});

describe("projection states", () => {
  it("normal proposition carries evidence and confidence", () => {
    const view = projectPov({
      propositions: [
        prop({
          confidence: "high",
          last_reviewed: "2026-09-19T00:00:00Z",
          supporting: [
            {
              slot: "measurement",
              polarity: "supporting",
              text: "Evidence.",
              claim_id: "abc123",
              event_id: "ev1",
              confidence: "high",
            },
          ],
        }),
      ],
    });
    const p = view.propositions[0];
    expect(p.confidence).toBe("high");
    expect(p.supporting).toHaveLength(1);
    expect(isUnresolved(p)).toBe(false);
    expect(isContested(p)).toBe(false);
  });

  it("unresolved proposition has no evidence and null last_reviewed", () => {
    const view = projectPov({ propositions: [prop()] });
    const p = view.propositions[0];
    expect(isUnresolved(p)).toBe(true);
    expect(p.last_reviewed).toBeNull();
    expect(formatDate(p.last_reviewed)).toBe("not yet reviewed");
  });

  it("contested proposition is capped and flagged when contradicting evidence exists", () => {
    const view = projectPov({
      propositions: [
        prop({
          confidence: "low",
          supporting: [
            { slot: "measurement", polarity: "supporting", text: "Supports.", claim_id: "s1", event_id: "e1", confidence: "high" },
          ],
          contradicting: [
            { slot: "measurement", polarity: "contradicting", text: "Contradicts.", claim_id: "c1", event_id: "e2", confidence: "medium" },
          ],
        }),
      ],
    });
    const p = view.propositions[0];
    expect(isContested(p)).toBe(true);
    expect(p.contested).toBe(true);
    expect(p.confidence).toBe("low");
  });

  it("contested flag is inferred from contradicting evidence even if unset", () => {
    const view = projectPov({
      propositions: [
        prop({
          contested: false,
          contradicting: [
            { slot: "measurement", polarity: "contradicting", text: "Contradicts.", claim_id: "c1", event_id: "e2", confidence: "low" },
          ],
        }),
      ],
    });
    expect(view.propositions[0].contested).toBe(true);
  });

  it("changed proposition produces an ordered changelog with before and after", () => {
    const view = projectPov({
      propositions: [prop({ confidence: "medium" })],
      changelog: [
        {
          proposition_id: "pov-test",
          changed_at: "2026-09-18T00:00:00Z",
          reason: "later",
          event_id: "e2",
          evidence_ids: [],
          old_statement: "old2",
          new_statement: "new2",
          significance: 3.6,
          confidence: "medium",
        },
        {
          proposition_id: "pov-test",
          changed_at: "2026-09-17T00:00:00Z",
          reason: "earlier",
          event_id: "e1",
          evidence_ids: ["x"],
          old_statement: "old1",
          new_statement: "new1",
          significance: 3.9,
          confidence: "high",
        },
      ],
    });
    expect(hasChanges(view)).toBe(true);
    expect(view.changelog.map((c) => c.reason)).toEqual(["earlier", "later"]);
    expect(view.changelog[0].old_statement).toBe("old1");
    expect(view.changelog[1].new_statement).toBe("new2");
  });

  it("empty changelog is a valid no-change outcome", () => {
    const view = projectPov({ propositions: [prop()], changelog: [] });
    expect(hasChanges(view)).toBe(false);
    expect(view.changelog).toHaveLength(0);
  });

  it("rejects an artifact with no propositions", () => {
    expect(() => projectPov({ propositions: [] })).toThrow(/no POV propositions/);
  });
});

describe("presentation helpers", () => {
  it("labels every confidence value", () => {
    for (const label of ["high", "medium_high", "medium", "low", "unresolved"] as const) {
      expect(CONFIDENCE_LABELS[label]).toBeTruthy();
    }
  });

  it("formats dates deterministically in UTC", () => {
    expect(formatDate("2026-09-19T18:33:41.589716Z")).toBe("2026-09-19");
    expect(formatDateTime("2026-09-19T18:33:41.589716Z")).toBe("2026-09-19 18:33 UTC");
  });

  it("links evidence ids into the observation plane", () => {
    expect(evidenceHref("abc")).toBe("/?evidence=abc");
    expect(evidenceHref("a b")).toBe("/?evidence=a%20b");
  });
});
