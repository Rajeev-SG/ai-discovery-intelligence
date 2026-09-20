import { describe, expect, it } from "vitest";
import {
  CONFIDENCE_LABELS,
  evidenceHref,
  formatDate,
  formatDateTime,
  hasChanges,
  isContested,
  isUnresolved,
  projectPov,
} from "../lib/pov";
import { loadPov } from "../lib/pov.server";

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

/**
 * The canonical proposition ids, emitted into the artifact by
 * scripts/build_web_pov.py straight from pov/state.yaml (which asserts the
 * projection covers exactly those ids). Reading them from the artifact keeps
 * the test structural — no hard-coded ids or claim hashes, and no second YAML
 * parser in the web suite.
 */

describe("canonical POV artifact", () => {
  const view = loadPov();

  it("covers exactly the propositions in pov/state.yaml", () => {
    const ids = view.propositions.map((p) => p.id);
    // canonical_ids is the authoritative state.yaml id set, emitted by the
    // generator after asserting artifact coverage.
    expect(view.canonical_ids.length).toBeGreaterThan(0);
    expect(ids).toEqual(view.canonical_ids);
    expect(new Set(ids).size).toBe(ids.length);
  });

  it("renders every proposition's canonical confidence verbatim", () => {
    const labels = new Set(Object.keys(CONFIDENCE_LABELS));
    for (const proposition of view.propositions) {
      expect(labels.has(proposition.confidence)).toBe(true);
      // isUnresolved/isContested are pure projections of the artifact fields.
      expect(isUnresolved(proposition)).toBe(proposition.confidence === "unresolved");
      expect(isContested(proposition)).toBe(proposition.contested);
    }
  });

  it("renders a proposition with evidence and its matching changelog entry", () => {
    const withEvidence = view.propositions.filter((p) => p.supporting.length > 0);
    expect(withEvidence.length).toBeGreaterThan(0);
    for (const proposition of withEvidence) {
      expect(proposition.confidence).not.toBe("unresolved");
      expect(proposition.last_reviewed).not.toBeNull();
      for (const bullet of proposition.supporting) {
        expect(bullet.claim_id.length).toBeGreaterThan(0);
        // A change that adopted this evidence is recorded in the changelog.
        const change = view.changelog.find(
          (c) => c.proposition_id === proposition.id && c.evidence_ids.includes(bullet.claim_id),
        );
        expect(change, `no changelog entry grounds ${proposition.id} claim ${bullet.claim_id}`).toBeTruthy();
      }
    }
  });

  it("renders at least one proposition as unresolved with no evidence", () => {
    const unresolved = view.propositions.filter(isUnresolved);
    expect(unresolved.length).toBeGreaterThan(0);
    for (const proposition of unresolved) {
      expect(proposition.supporting).toHaveLength(0);
      expect(proposition.contradicting).toHaveLength(0);
      expect(proposition.contested).toBe(false);
      expect(proposition.last_reviewed).toBeNull();
    }
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

  it("contested proposition is flagged verbatim from the artifact field", () => {
    const view = projectPov({
      propositions: [
        prop({
          confidence: "low",
          contested: true,
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

  it("does not invent contested state: artifact flag is authoritative", () => {
    // Contradicting evidence present but the canonical model says not contested.
    // The projection must render the flag as-is, not re-derive from the list.
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
    expect(view.propositions[0].contested).toBe(false);
    expect(isContested(view.propositions[0])).toBe(false);
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
    expect(evidenceHref("abc")).toBe("/surfaces?evidence=abc");
    expect(evidenceHref("a b")).toBe("/surfaces?evidence=a%20b");
  });
});
