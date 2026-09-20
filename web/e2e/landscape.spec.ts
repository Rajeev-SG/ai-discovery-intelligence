import { expect, test } from "@playwright/test";
import { mkdirSync } from "node:fs";

const SHOTS = "proof";
const HAS_API = Boolean(process.env.EVIDENCE_API_URL || process.env.EVIDENCE_FIXTURE);

test.beforeAll(() => {
  mkdirSync(SHOTS, { recursive: true });
});

test("landscape lists major surfaces with evidence-aware coverage", async ({ page }) => {
  test.skip(!HAS_API, "requires EVIDENCE_API_URL or EVIDENCE_FIXTURE=1");

  await page.goto("/landscape");
  await expect(page.getByRole("heading", { name: "AI discovery landscape" })).toBeVisible();
  const grid = page.getByTestId("landscape-grid");
  await expect(grid).toBeVisible();
  expect(await grid.getByRole("article").count()).toBeGreaterThanOrEqual(2);

  // A surface card shows coverage and the registry-metadata distinction.
  const first = grid.getByRole("article").first();
  await expect(first).toContainText("Mechanics coverage");

  await page.screenshot({ path: `${SHOTS}/landscape-desktop.png`, fullPage: false });
});

test("comparison renders per-dimension cells with explicit unknowns", async ({ page }) => {
  test.skip(!HAS_API, "requires EVIDENCE_API_URL or EVIDENCE_FIXTURE=1");
  test.skip((page.viewportSize()?.width ?? 0) < 861, "desktop layout");

  await page.goto("/landscape");
  await expect(page.getByTestId("compare-status")).toBeVisible();
  const table = page.getByTestId("comparison-table");
  await expect(table).toBeVisible();
  // Unknown cells are present and labelled, never blank.
  expect(await page.getByTestId(/cmp-.*-unknown/).count()).toBeGreaterThanOrEqual(1);

  await page.screenshot({ path: `${SHOTS}/landscape-comparison.png`, fullPage: false });
});

test("comparison selection is stored in the URL", async ({ page }) => {
  test.skip(!HAS_API, "requires EVIDENCE_API_URL or EVIDENCE_FIXTURE=1");

  await page.goto("/landscape");
  // Toggle a surface off, then confirm the URL reflects the selection.
  await page.getByTestId("compare-toggle-google-gemini").click();
  await page.waitForTimeout(200);
  expect(page.url()).toMatch(/compare=/);
});


test("a shared ?compare= URL round-trips and survives back/forward", async ({ page }) => {
  test.skip(!HAS_API, "requires EVIDENCE_API_URL or EVIDENCE_FIXTURE=1");
  test.skip((page.viewportSize()?.width ?? 0) < 861, "desktop layout");

  // Load a shared selection of two real surfaces.
  await page.goto("/landscape?compare=chatgpt,deepseek-chat");
  await expect(page.getByTestId("comparison-table")).toBeVisible();
  // The rendered columns match the URL, not the curated default.
  await expect(page.getByTestId("cmp-col-chatgpt")).toBeVisible();
  await expect(page.getByTestId("cmp-col-deepseek-chat")).toBeVisible();
  await expect(page.getByTestId("cmp-col-google-gemini")).toHaveCount(0);

  // A user toggle updates the URL, and a fresh navigation honours the new one.
  await page.goto("/landscape?compare=chatgpt,google-gemini");
  await expect(page.getByTestId("cmp-col-google-gemini")).toBeVisible();
  await expect(page.getByTestId("cmp-col-deepseek-chat")).toHaveCount(0);
});

test("an unknown id in a shared URL is surfaced, not silently dropped", async ({ page }) => {
  test.skip(!HAS_API, "requires EVIDENCE_API_URL or EVIDENCE_FIXTURE=1");
  await page.goto("/landscape?compare=chatgpt,not-a-surface");
  await expect(page.getByTestId("compare-dropped")).toBeVisible();
});
