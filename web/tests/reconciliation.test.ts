import { describe, expect, it } from "vitest";
import {
  formatAdjustment,
  formatValue,
  indexClaims,
  isContested,
  joinReconciliation,
  joinRelationship,
  splitClaimRef,
  stateCategory,
  type ReconClaim,
  type ReconciliationItem,
} from "../lib/reconciliation";

function claim(overrides: Partial<ReconClaim> & { claim_id: string }): ReconClaim {
  return {
    topic: "audience_usage",
    statement: "Placeholder claim",
    surfaces: [],
    value: [],
    ...overrides,
  };
}

const semrush = claim({
  claim_id: "aaa",
  statement: "Reddit cited in ChatGPT answers for 12% of tracked prompts (Semrush).",
  surfaces: ["chatgpt"],
  value: [
    {
      metric_id: "m1",
      label: "share of answers",
      value_number: 12,
      value_text: "12",
      unit: "percent",
      window: "2026-06",
      scope: "US",
      known: true,
    },
  ],
  dates: { observed_at: "2026-06-30T00:00:00Z" },
});

const ahrefs = claim({
  claim_id: "bbb",
  statement: "Reddit is the top-cited domain in ChatGPT answers (Ahrefs).",
  surfaces: ["chatgpt"],
  value: [
    {
      metric_id: "m1",
      label: "citation rank",
      value_number: 1,
      value_text: "#1",
      unit: "rank",
      window: "2026-05",
      scope: "Global",
      known: true,
    },
  ],
  dates: { observed_at: "2026-05-31T00:00:00Z" },
});

const incomparable: ReconciliationItem = {
  claim_ids: ["aaa:m1", "bbb:m1"],
  state: "methodologically_incomparable",
  relationship: "contextualises",
  confidence_adjustment: -0.15,
  differences: ["metric", "unit"],
  unknown_dimensions: ["denominator", "geography"],
  interpretation:
    "These findings differ in metric and unit and cannot be reconciled as estimates of the same quantity. Preserve both.",
};

describe("claim_ids -> claim join", () => {
  it("splits the :metricid suffix", () => {
    expect(splitClaimRef("abc123:m2")).toEqual({ raw: "abc123:m2", claim_id: "abc123", metric_id: "m2" });
  });

  it("tolerates a bare claim id with no metric suffix", () => {
    expect(splitClaimRef("abc123")).toEqual({ raw: "abc123", claim_id: "abc123", metric_id: null });
  });

  it("resolves both sides to the real claim and the referenced metric", () => {
    const byId = indexClaims([semrush, ahrefs]);
    const resolved = joinRelationship(incomparable, byId);
    expect(resolved.sides).toHaveLength(2);
    expect(resolved.sides[0].claim?.claim_id).toBe("aaa");
    expect(resolved.sides[0].metric?.metric_id).toBe("m1");
    expect(resolved.sides[0].surface).toBe("chatgpt");
    expect(resolved.sides[1].claim?.statement).toContain("Ahrefs");
    expect(resolved.sides[1].metric?.label).toBe("citation rank");
  });

  it("keeps a side with a claim the ledger does not hold inspectable as missing", () => {
    const byId = indexClaims([semrush]);
    const resolved = joinRelationship(incomparable, byId);
    expect(resolved.sides[1].claim).toBeNull();
    expect(resolved.sides[0].claim?.claim_id).toBe("aaa");
  });

  it("joins the whole response and preserves every original claim", () => {
    const joined = joinReconciliation({ count: 1, items: [incomparable] }, [semrush, ahrefs]);
    expect(joined).toHaveLength(1);
    const statements = joined[0].sides.map((s) => s.claim?.statement);
    expect(statements).toHaveLength(2);
    expect(statements.every(Boolean)).toBe(true);
  });
});

describe("contextualisation / incomparability", () => {
  it("classifies a metric/unit difference as incomparable without collapsing the claims", () => {
    const resolved = joinRelationship(incomparable, indexClaims([semrush, ahrefs]));
    expect(resolved.category).toBe("incomparable");
    expect(resolved.contested).toBe(false);
    expect(resolved.item.differences).toContain("metric");
    expect(resolved.item.unknown_dimensions).toContain("denominator");
    expect(resolved.sides.map((s) => s.claim?.claim_id)).toEqual(["aaa", "bbb"]);
  });
});

describe("contradiction", () => {
  const conflict: ReconciliationItem = {
    claim_ids: ["aaa:m1", "bbb:m1"],
    state: "material_conflict",
    relationship: "contradicts",
    confidence_adjustment: -0.3,
    differences: [],
    unknown_dimensions: [],
    interpretation: "Directly conflicting values on the same metric.",
  };

  it("is a contested, distinct category", () => {
    expect(stateCategory("material_conflict")).toBe("conflict");
    expect(isContested("material_conflict")).toBe(true);
    const resolved = joinRelationship(conflict, indexClaims([semrush, ahrefs]));
    expect(resolved.category).toBe("conflict");
    expect(resolved.contested).toBe(true);
    expect(resolved.sides).toHaveLength(2);
  });
});

describe("supersession", () => {
  const update: ReconciliationItem = {
    claim_ids: ["aaa:m1", "bbb:m1"],
    state: "temporal_update",
    relationship: "supersedes",
    confidence_adjustment: 0,
    differences: ["period_start"],
    unknown_dimensions: [],
    interpretation: "The newer measurement supersedes the older window.",
  };

  it("marks the older evidence superseded while keeping it inspectable", () => {
    const resolved = joinRelationship(update, indexClaims([semrush, ahrefs]));
    const superseded = resolved.sides.filter((s) => s.superseded);
    expect(superseded).toHaveLength(1);
    // Ahrefs (May) precedes Semrush (June), so the older side is the superseded one.
    expect(superseded[0].claim?.claim_id).toBe("bbb");
    // Both sides are still rendered.
    expect(resolved.sides).toHaveLength(2);
    expect(resolved.sides.every((s) => s.claim !== null)).toBe(true);
  });

  it("marks nothing when a supersedes/updates side has no observation time", () => {
    const noDates = [semrush, { ...ahrefs, dates: {} }];
    const resolved = joinRelationship(update, indexClaims(noDates));
    expect(resolved.sides.some((s) => s.superseded)).toBe(false);
    expect(resolved.sides).toHaveLength(2);
  });

  it("never marks a side for possible_transient_change (it asserts no precedence)", () => {
    const transient: ReconciliationItem = {
      ...update,
      state: "possible_transient_change",
      relationship: "contextualises",
    };
    const resolved = joinRelationship(transient, indexClaims([semrush, ahrefs]));
    expect(resolved.sides.some((s) => s.superseded)).toBe(false);
    expect(resolved.category).toBe("temporal");
  });
});

describe("claims-ledger failure mode", () => {
  it("flags every side as ledger-unavailable when the claim ledger cannot be read", () => {
    const joined = joinReconciliation({ count: 1, items: [incomparable] }, null);
    expect(joined[0].sides).toHaveLength(2);
    expect(joined[0].sides.every((s) => s.claim === null)).toBe(true);
    expect(joined[0].sides.every((s) => s.ledgerUnavailable)).toBe(true);
  });

  it("does not flag ledger-unavailable when the ledger loaded but a claim is absent", () => {
    const joined = joinReconciliation({ count: 1, items: [incomparable] }, [semrush]);
    const missing = joined[0].sides[1];
    expect(missing.claim).toBeNull();
    expect(missing.ledgerUnavailable).toBe(false);
  });
});

describe("key collisions", () => {
  it("keeps two relationships with identical (claims, relationship, state) distinct", () => {
    const a = incomparable;
    const b: ReconciliationItem = { ...incomparable, interpretation: "Second, different interpretation." };
    const joined = joinReconciliation({ count: 2, items: [a, b] }, [semrush, ahrefs]);
    expect(joined).toHaveLength(2);
    // The list keys on category+index, so both survive with their own interpretation.
    expect(joined[1].item.interpretation).toBe("Second, different interpretation.");
  });
});

describe("formatting helpers", () => {
  it("never invents a number and renders units", () => {
    expect(formatValue(semrush.value[0])).toBe("12 percent");
    expect(formatValue({ ...semrush.value[0], known: false })).toBe("Unknown value");
    expect(formatValue(null)).toBe("Unknown value");
  });

  it("signs the confidence adjustment", () => {
    expect(formatAdjustment(-0.15)).toBe("\u22120.15");
    expect(formatAdjustment(0.2)).toBe("+0.2");
    expect(formatAdjustment(null)).toBe("none");
  });
});
