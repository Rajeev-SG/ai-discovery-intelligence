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

  // The front door answers the marketer's questions, not the analyst's feed
  // (issue #61): above the fold states what the product is for, in marketer terms.
  const h1 = page.getByRole("heading", { level: 1 });
  await expect(h1).toContainText(/AI discovery|discovery works/i);
  // The four questions are first-class and link to the four destinations.
  for (const q of ["home-q1", "home-q2", "home-q3", "home-q4"]) {
    await expect(page.getByTestId(q)).toBeVisible();
  }
  await expect(page.getByTestId("home-questions")).toContainText("What AI discovery platforms exist?");
  await expect(page.getByTestId("home-questions")).toContainText("Why does this matter for marketers?");

  // Each section renders exactly one of populated / explicit-empty / unavailable.
  await assertSingleState(page, "landing-changes", ["change-list", "changes-empty", "changes-unavailable"]);
  await assertSingleState(page, "landing-brief", ["brief-list", "brief-empty", "brief-unavailable"]);
  await assertSingleState(page, "landing-pov", ["pov-summary"]);

  // POV is canonical (committed artifact), so it must always have propositions.
  expect(await page.getByTestId("pov-summary").locator("> li").count()).toBeGreaterThanOrEqual(1);

  // Internal architecture terms no longer drive the primary navigation: the
  // primary list and the secondary "More" list are STRUCTURALLY separate (F2).
  const primaryNav = page.getByRole("navigation", { name: "Product surfaces" });
  const primaryList = primaryNav.locator(".site-nav-primary");
  const secondaryList = primaryNav.getByRole("list", { name: "More" });
  await expect(primaryList).toBeVisible();
  await expect(secondaryList).toBeVisible();
  const primaryText = await primaryList.innerText();
  expect(primaryText).not.toMatch(/POV|Reconciliation|What this means|Evidence reconciliation/);
  // The demoted destinations remain reachable in the secondary list.
  await expect(secondaryList.getByRole("link", { name: "What this means" })).toBeVisible();
  await expect(secondaryList.getByRole("link", { name: "Evidence reconciliation" })).toBeVisible();

  // Latest changes / weekly brief are demoted below the questions.
  await expect(page.getByTestId("home-latest-title")).toContainText(/Latest changes/i);

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
    const count = await items.count();
    expect(count).toBeGreaterThanOrEqual(1);
    expect((await items.first().innerText()).trim().length).toBeGreaterThan(10);

    // Truncation disclosure must agree with the section's own shown/total data
    // attributes (which mirror the rendered list), and be present iff the total
    // exceeds what was shown. Reading the real totals avoids pinning the cap or
    // the copy wording, and makes BOTH branches assert — a missing disclosure on
    // a truncated feed fails, and a spurious one on a short feed fails too.
    const shown = Number(await changes.getAttribute("data-change-shown"));
    const total = Number(await changes.getAttribute("data-change-total"));
    expect(shown).toBe(count);
    const truncation = changes.getByTestId("changes-truncation");
    if (total > shown) {
      await expect(truncation).toBeVisible();
      await expect(truncation).toContainText(`of ${total}`);
    } else {
      await expect(truncation).toHaveCount(0);
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


test("with no backend, the questions render explicit unavailable answers (not implied zero)", async ({ page }) => {
  // F1: a backend outage must be distinguishable from a reachable-but-empty
  // source. This test only runs in a no-API environment, so it is skipped when a
  // live API is wired in (where the populated answers are the correct state).
  test.skip(HAS_API, "no-API environment only");
  await page.goto("/");
  const questions = page.getByTestId("home-questions");
  await expect(questions).toBeVisible();
  // Each question reports the unavailable state explicitly.
  const unavailable = questions.locator('[data-state="unavailable"]');
  expect(await unavailable.count()).toBeGreaterThanOrEqual(1);
  await expect(questions).toContainText(/unavailable right now/i);
});
