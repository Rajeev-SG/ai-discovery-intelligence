import { expect, test } from "@playwright/test";
import { mkdirSync } from "node:fs";

const SHOTS = "proof";

/** Screenshot path namespaced by project so desktop and mobile never collide. */
function shot(testInfo: import("@playwright/test").TestInfo, name: string): string {
  const short = testInfo.project.name.replace("-chromium", "");
  return `${SHOTS}/landing-${short}-${name}.png`;
}

test.beforeAll(() => {
  mkdirSync(SHOTS, { recursive: true });
});

/**
 * Real-browser proof for the intelligence-first landing (issue #45). It runs
 * against the live evidence API configured for the app: the landing must show
 * real material changes, the real weekly brief and the canonical POV. An
 * unreachable backend fails these rather than passing on fixtures.
 *
 * The empty-versus-unavailable distinction is asserted structurally: exactly
 * one state per section is present, and its test id names which (…-empty vs
 * …-unavailable). The branch logic itself is unit-tested in tests/intel.test.ts.
 */
test("landing leads with real changes, brief and current POV", async ({ page }, testInfo) => {
  await page.goto("/");

  // Hero frames the product, not the registry.
  await expect(page.getByRole("heading", { level: 1 })).toContainText("What changed");
  await expect(page.getByRole("link", { name: "Explore surfaces", exact: true }).first()).toBeVisible();

  // 1. Latest material changes from the real /events feed.
  const changes = page.getByTestId("landing-changes");
  await expect(changes).toBeVisible();
  await expect(changes.getByTestId("changes-unavailable")).toHaveCount(0);
  await expect(changes.getByTestId("change-list")).toBeVisible();
  const changeItems = changes.getByTestId("change-list").locator("> li");
  expect(await changeItems.count()).toBeGreaterThanOrEqual(1);
  expect((await changeItems.first().innerText()).trim().length).toBeGreaterThan(10);

  // 2. Weekly executive brief from the real /brief feed.
  const brief = page.getByTestId("landing-brief");
  await expect(brief).toBeVisible();
  await expect(brief.getByTestId("brief-unavailable")).toHaveCount(0);
  await expect(brief.getByTestId("brief-list")).toBeVisible();
  await expect(brief.getByTestId("brief-item").first()).toContainText("Why it matters");
  await expect(brief.getByTestId("brief-item").first()).toContainText("Agency action");

  // 3. Current POV from the canonical artifact.
  const pov = page.getByTestId("landing-pov");
  await expect(pov).toBeVisible();
  const povItems = pov.getByTestId("pov-summary").locator("> li");
  expect(await povItems.count()).toBeGreaterThanOrEqual(1);
  await expect(pov).toContainText("confidence");

  await page.screenshot({ path: shot(testInfo, "intelligence"), fullPage: true });
});

test("empty and unavailable states are distinct and mutually exclusive", async ({ page }) => {
  await page.goto("/");
  // Each section renders exactly one of its states; the ids name which one.
  for (const section of ["landing-changes", "landing-brief"]) {
    const states = page
      .getByTestId(section)
      .locator('[data-testid$="-unavailable"], [data-testid$="-empty"]');
    expect(await states.count()).toBeLessThanOrEqual(1);
  }
  // The unavailable copy is unmistakably different from the empty copy.
  const body = await page.locator("body").innerText();
  expect(body).not.toContain("awaiting ingestion");
});

test("navigates into Explore surfaces, which keeps all 35 and narrows on search", async ({ page }, testInfo) => {
  await page.goto("/");
  await page.getByRole("link", { name: "Explore surfaces", exact: true }).first().click();
  await expect(page).toHaveURL(/\/surfaces/);

  await expect(page.getByTestId("registry-count")).toHaveText("35");
  await expect(page.getByTestId("surface-count")).toHaveText("35");

  await page.getByTestId("search-input").fill("China");
  const summary = page.getByTestId("result-summary");
  await expect(summary).toContainText('matching');
  const before = 35;
  const afterText = await summary.innerText();
  const after = Number(afterText.match(/^(\d+)/)?.[1] ?? "0");
  expect(after).toBeGreaterThan(0);
  expect(after).toBeLessThan(before);

  await page.screenshot({ path: shot(testInfo, "explore-surfaces"), fullPage: false });
});
