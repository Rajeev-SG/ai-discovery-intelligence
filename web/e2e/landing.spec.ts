import { expect, test } from "@playwright/test";
import { mkdirSync } from "node:fs";

const SHOTS = "proof";
const HAS_API = Boolean(process.env.EVIDENCE_API_URL || process.env.EVIDENCE_FIXTURE);

/** Screenshot path namespaced by project so desktop and mobile never collide. */
function shot(testInfo: import("@playwright/test").TestInfo, name: string): string {
  const short = testInfo.project.name.replace("-chromium", "");
  return `${SHOTS}/landing-${short}-${name}.png`;
}

test.beforeAll(() => {
  mkdirSync(SHOTS, { recursive: true });
});

/**
 * Landing proof for issue #45. This file is portable: on a fresh clone with no
 * `EVIDENCE_API_URL` the landing renders its explicit unavailable states and
 * these tests still pass. The live-data assertions only run when the API is
 * configured (matching the `HAS_API` convention in `evidence-drilldown.spec.ts`),
 * so a healthy-but-empty backend is also a passing case.
 *
 * The invariant asserted everywhere is structural: each section renders EXACTLY
 * ONE of its mutually-exclusive states — populated, explicit-empty, or
 * unavailable — and never more than one, and never none.
 */
async function assertSingleState(
  page: import("@playwright/test").Page,
  section: string,
  stateIds: string[],
): Promise<void> {
  const scope = page.getByTestId(section);
  await expect(scope).toBeVisible();
  const present = await scope
    .locator(stateIds.map((id) => `[data-testid="${id}"]`).join(", "))
    .count();
  expect(present, `${section} must render exactly one state`).toBe(1);
}

test("landing renders a single, well-formed state per section", async ({ page }, testInfo) => {
  await page.goto("/");

  // Hero frames the product, not the registry.
  await expect(page.getByRole("heading", { level: 1 })).toContainText("What changed");
  await expect(page.getByRole("link", { name: "Explore surfaces", exact: true }).first()).toBeVisible();

  // Each section renders exactly one of populated / explicit-empty / unavailable.
  await assertSingleState(page, "landing-changes", ["change-list", "changes-empty", "changes-unavailable"]);
  await assertSingleState(page, "landing-brief", ["brief-list", "brief-empty", "brief-unavailable"]);
  await assertSingleState(page, "landing-pov", ["pov-summary"]);

  // POV is canonical (committed artifact), so it must always have propositions.
  expect(await page.getByTestId("pov-summary").locator("> li").count()).toBeGreaterThanOrEqual(1);

  // The stale "awaiting ingestion" copy is nowhere on the landing.
  expect(await page.locator("body").innerText()).not.toContain("awaiting ingestion");

  await page.screenshot({ path: shot(testInfo, "intelligence"), fullPage: true });
});

test("landing shows real changes, brief and current POV from the live API", async ({ page }, testInfo) => {
  test.skip(!HAS_API, "requires EVIDENCE_API_URL or EVIDENCE_FIXTURE=1");
  await page.goto("/");

  const changes = page.getByTestId("landing-changes");
  const brief = page.getByTestId("landing-brief");

  // Live API configured: the landing must NOT render the unavailable state, and
  // must either show populated data or the honest empty state (both valid).
  await expect(changes.getByTestId("changes-unavailable")).toHaveCount(0);
  await expect(brief.getByTestId("brief-unavailable")).toHaveCount(0);

  const changeList = changes.getByTestId("change-list");
  if ((await changeList.count()) > 0) {
    const items = changeList.locator("> li");
    expect(await items.count()).toBeGreaterThanOrEqual(1);
    expect((await items.first().innerText()).trim().length).toBeGreaterThan(10);
    // Truncation is disclosed when the feed exceeds the landing's limit.
    if ((await items.count()) === 8) {
      await expect(changes.getByTestId("changes-truncation")).toBeVisible();
    }
    await page.screenshot({ path: shot(testInfo, "changes"), fullPage: false });
  } else {
    await expect(changes.getByTestId("changes-empty")).toBeVisible();
  }

  const briefList = brief.getByTestId("brief-list");
  if ((await briefList.count()) > 0) {
    const first = brief.getByTestId("brief-item").first();
    // The standing "why it matters / agency action" framing is disclosed behind a
    // per-card expander (the copy repeats across items), so open it before checking.
    await first.locator("details summary").first().click();
    await expect(first).toContainText("Why it matters");
    await expect(first).toContainText("Agency action");
    await page.screenshot({ path: shot(testInfo, "brief"), fullPage: false });
  } else {
    await expect(brief.getByTestId("brief-empty")).toBeVisible();
  }
});

test("empty and unavailable states are distinct and mutually exclusive", async ({ page }) => {
  await page.goto("/");
  for (const section of ["landing-changes", "landing-brief"]) {
    const states = page.getByTestId(section).locator('[data-testid$="-unavailable"], [data-testid$="-empty"]');
    expect(await states.count()).toBeLessThanOrEqual(1);
  }
  const body = await page.locator("body").innerText();
  expect(body).not.toContain("awaiting ingestion");
  // The unavailable copy and the empty copy are worded differently.
  expect(body).not.toMatch(/not reachable right now[\s\S]*no material item qualifies/);
});

test("navigates into Explore surfaces, which keeps all 35 and narrows on search", async ({ page }, testInfo) => {
  await page.goto("/");
  await page.getByRole("link", { name: "Explore surfaces", exact: true }).first().click();
  await expect(page).toHaveURL(/\/surfaces/);

  await expect(page.getByTestId("registry-count")).toHaveText("35");
  await expect(page.getByTestId("surface-count")).toHaveText("35");

  await page.getByTestId("search-input").fill("China");
  const summary = page.getByTestId("result-summary");
  await expect(summary).toContainText("matching");
  const after = Number((await summary.innerText()).match(/^(\d+)/)?.[1] ?? "0");
  expect(after).toBeGreaterThan(0);
  expect(after).toBeLessThan(35);

  await page.screenshot({ path: shot(testInfo, "explore-surfaces"), fullPage: false });
});
