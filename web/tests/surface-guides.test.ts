import { describe, expect, it } from "vitest";
import comingSoon from "../content/coming-soon.json";
import registry from "../lib/generated-registry.json";
import { formatCheckedDate, loadSurfaceGuides } from "../lib/surface-guides";

describe("editorial surface guides", () => {
  const guides = loadSurfaceGuides();

  // These tests pin *structure*, not wording. Publishing is now partly
  // machine-assisted (deploy/writer), so any assertion on exact action titles,
  // change dates or source counts would fail on a legitimate content update and
  // teach everyone to loosen it under pressure. What must not drift is the
  // shape a reader depends on: the seven mechanics labels in order, at least
  // three concrete actions, at least one dated change, and real source links.
  // Exact prose is gated elsewhere, against evidence, before it can merge.
  it("loads the ChatGPT guide in the target's editorial order", () => {
    const guide = guides.get("chatgpt")!;
    expect(guide.vendor).toBe("OpenAI");
    expect(guide.mechanics.map(({ label }) => label)).toEqual([
      "When it searches", "Where results come from", "Crawlers",
      "Keeping a page out", "Shopping", "Ads", "Measurement",
    ]);
    const crawlers = guide.mechanics[2];
    expect("crawlers" in crawlers && crawlers.crawlers.length).toBeGreaterThan(0);
  });

  it("uses real source links and an unambiguous check date on published guides", () => {
    for (const guide of guides.values()) {
      expect(guide.sources.length).toBeGreaterThan(0);
      for (const source of guide.sources) {
        expect(new URL(source.url).protocol).toBe("https:");
        expect(source.checked).toMatch(/^\d{4}-\d{2}-\d{2}$/);
        expect(formatCheckedDate(source.checked)).toMatch(/^\d{1,2} \w{3} \d{4}$/);
      }
    }
    expect(formatCheckedDate("2026-11-17")).toBe("17 Nov 2026");
  });

  it("gives each published guide concrete actions and each unpublished surface a reason", () => {
    const googleSearchSurfaces = new Set(["google-ai-mode", "google-ai-overviews"]);
    const unpublished = registry.surfaces
      .filter(({ id }) => !guides.has(id) && !googleSearchSurfaces.has(id))
      .map(({ id }) => id);
    expect(Object.keys(comingSoon).sort()).toEqual(unpublished.sort());
    for (const reason of Object.values(comingSoon)) expect(reason.trim()).not.toBe("");
    for (const guide of guides.values()) {
      expect(guide.actions.length).toBeGreaterThanOrEqual(3);
      expect(guide.mechanics).toHaveLength(7);
      expect(guide.changes.length).toBeGreaterThan(0);
    }
  });
});
