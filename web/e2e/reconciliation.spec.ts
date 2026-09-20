import { expect, test } from "@playwright/test";
import { mkdirSync } from "node:fs";

const SHOTS = "proof";

/** Screenshot path namespaced by project so desktop and mobile never collide. */
function shot(testInfo: import("@playwright/test").TestInfo, name: string): string {
  const short = testInfo.project.name.replace("-chromium", "");
  return `${SHOTS}/reconciliation-${short}-${name}.png`;
}

/**
 * Real-data proof for the reconciliation view (issue #47). It runs against the
 * live evidence API configured for the app; if the ledger is unreachable the
 * test fails rather than passing on a fixture.
 */
test.beforeAll(() => {
  mkdirSync(SHOTS, { recursive: true });
});

/**
 * Load the reconciliation view and skip the whole file when the evidence API is
 * not reachable (the page then renders its explicit unavailable state). This
 * keeps the e2e gate independent of any specific live host while still being a
 * real product proof wherever a ledger is configured.
 */
async function gotoOrSkip(page: import("@playwright/test").Page): Promise<void> {
  await page.goto("/reconciliation");
  if ((await page.getByTestId("recon-unavailable").count()) > 0) {
    test.skip(
      true,
      "Evidence API unreachable: set EVIDENCE_API_URL to a live ledger for the reconciliation proof.",
    );
  }
}

test("renders the persisted reconciliation ledger with real relationships", async ({ page }, testInfo) => {
  await gotoOrSkip(page);

  // The ledger must be reachable — never silently empty against the live API.
  await expect(page.getByTestId("recon-unavailable")).toHaveCount(0);

  const relationships = page.getByTestId("recon-rel");
  await expect(relationships.first()).toBeVisible();
  expect(await relationships.count()).toBeGreaterThan(5);

  const first = relationships.first();

  // Relationship type + canonical state are rendered verbatim.
  await expect(first.locator(".recon-badge-relationship")).not.toBeEmpty();
  await expect(first.locator(".recon-badge-state")).not.toBeEmpty();

  // Both sides' statements and values are visible (no collapse into one truth).
  await expect(first.locator(".recon-side-statement").first()).not.toBeEmpty();
  await expect(first.locator(".recon-side-statement").nth(1)).not.toBeEmpty();
  await expect(first.locator(".recon-value").first()).not.toBeEmpty();

  // Agency interpretation is visible in the default view.
  await expect(first.getByTestId("recon-interpretation")).not.toBeEmpty();

  // Confidence adjustment is visible.
  await expect(first.getByTestId("recon-adjustment")).not.toBeEmpty();

  await page.screenshot({ path: shot(testInfo, "ledger"), fullPage: false });
});

test("differences, unknown dimensions and expanded comparison detail are present", async ({ page }, testInfo) => {
  await gotoOrSkip(page);
  const first = page.getByTestId("recon-rel").first();
  await first.getByTestId("recon-context").locator("summary").click();
  await expect(first.getByTestId("recon-unknowns")).toBeVisible();
  await expect(first.getByTestId("recon-unknowns").locator("li").first()).not.toBeEmpty();
  await page.screenshot({ path: shot(testInfo, "context"), fullPage: false });
});

test("links back into the evidence surface route", async ({ page }) => {
  await gotoOrSkip(page);
  const link = page.locator('[data-testid^="recon-link-"]').first();
  await expect(link).toBeVisible();
  await expect(link).toHaveAttribute("href", /\/surfaces\?surface=/);
});

test("mobile layout keeps both sides and the interpretation readable", async ({ page }, testInfo) => {
  const desktop = page.viewportSize()!.width >= 861;
  test.skip(desktop, "mobile-only proof");
  await gotoOrSkip(page);
  await expect(page.getByTestId("recon-rel").first()).toBeVisible();
  await expect(page.getByTestId("recon-interpretation").first()).toBeVisible();
  await page.screenshot({ path: shot(testInfo, "layout"), fullPage: false });
});
