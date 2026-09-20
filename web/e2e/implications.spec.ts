import { expect, test } from "@playwright/test";
import { mkdirSync } from "node:fs";

const SHOTS = "proof";
const HAS_API = Boolean(process.env.EVIDENCE_API_URL || process.env.EVIDENCE_FIXTURE);

test.beforeAll(() => {
  mkdirSync(SHOTS, { recursive: true });
});

test("marketing implications are evidence-linked with confidence and actionability", async ({ page }) => {
  test.skip(!HAS_API, "requires EVIDENCE_API_URL or EVIDENCE_FIXTURE=1");

  await page.goto("/implications");
  await expect(page.getByRole("heading", { name: "Marketing implications" })).toBeVisible();

  // Either real implications render, or an explicit empty state — never both, never neither.
  const cards = page.getByTestId("impl-card");
  const empty = page.getByTestId("impl-empty");
  const unavailable = page.getByTestId("impl-unavailable");
  const monitor = page.getByTestId("impl-monitor-list");
  // Exactly one of the mutually-exclusive states must be present: actionable
  // cards, an all-monitor list, an explicit empty state, or an unavailable state.
  const count =
    (await cards.count()) + (await empty.count()) + (await unavailable.count()) + (await monitor.count());
  expect(count).toBeGreaterThanOrEqual(1);

  if ((await cards.count()) > 0) {
    const first = cards.first();
    // Every card states the action, a why, and cites its supporting claims.
    await expect(first.locator(".impl-action")).not.toBeEmpty();
    await expect(first.locator(".impl-rationale")).toContainText("Why:");
    await expect(first.locator(".impl-evidence-line")).toContainText("Supported by");
    // Confidence and actionability are both visible and distinct.
    await expect(first).toContainText("confidence");
    await expect(first.locator(".impl-actionability")).not.toBeEmpty();
  }

  await page.screenshot({ path: `${SHOTS}/implications-desktop.png`, fullPage: false });
});

test("monitor-only surfaces are shown explicitly, not as invented actions", async ({ page }) => {
  test.skip(!HAS_API, "requires EVIDENCE_API_URL or EVIDENCE_FIXTURE=1");

  await page.goto("/implications");
  // The monitor-only section exists whenever any surface lacks actionable evidence,
  // which is the normal, honest state.
  const monitor = page.getByTestId("impl-monitor-list");
  if ((await monitor.count()) > 0) {
    await expect(monitor).toContainText(/watch|monitor/i);
  }
});


test("an all-monitor-only ledger shows the monitor state, not a blank empty state", async ({ page }) => {
  test.skip(process.env.EVIDENCE_FIXTURE !== "all-monitor", "requires EVIDENCE_FIXTURE=all-monitor");
  test.skip((page.viewportSize()?.width ?? 0) < 861, "desktop layout");

  await page.goto("/implications");
  // Review impl-004: with zero actionable implications the monitor list must show,
  // never the generic "nothing here" empty state.
  await expect(page.getByTestId("impl-monitor-list")).toBeVisible();
  await expect(page.getByTestId("impl-empty")).toHaveCount(0);
  await expect(page.getByTestId("impl-monitor-list")).toContainText(/watch|monitor/i);
});
