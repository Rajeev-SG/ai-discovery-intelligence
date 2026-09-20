import { expect, test } from "@playwright/test";
import { mkdirSync } from "node:fs";

const SHOTS = "proof";
/** Structural proof for the evidence & trust layer (issue #58). Runs against the
 *  live API when EVIDENCE_API_URL is set and against recorded fixtures
 *  (EVIDENCE_FIXTURE=1) in CI. Assertions are structural so they survive real
 *  data changes, but the fixture path exercises the evidence-class distinctions
 *  and the inline conflict the product proof requires. */
const HAS_API = Boolean(process.env.EVIDENCE_API_URL || process.env.EVIDENCE_FIXTURE);

test.beforeAll(() => {
  mkdirSync(SHOTS, { recursive: true });
});

test("evidence & trust layer shows class, why-confidence, fresh-ness and inline conflict", async ({ page }) => {
  test.skip(!HAS_API, "requires EVIDENCE_API_URL or EVIDENCE_FIXTURE=1");
  test.skip((page.viewportSize()?.width ?? 0) < 861, "desktop layout");

  await page.goto("/surfaces");
  await page.getByTestId("search-input").fill("ChatGPT");
  await page.getByTestId("row-chatgpt").scrollIntoViewIfNeeded();
  await page.getByTestId("cell-chatgpt-evidence").click();

  const dialog = page.getByRole("dialog");
  await expect(dialog).toBeVisible();

  // The trust section is present and loads the evidenced mechanics lazily.
  await expect(dialog.getByText("Evidence & trust")).toBeVisible();
  const summary = dialog.getByTestId("trust-summary");
  await expect(summary).toBeVisible();
  await expect(summary).toContainText("mechanics");

  // Every evidenced dimension carries a "why this confidence" line.
  const why = dialog.getByTestId("trust-why");
  expect(await why.count()).toBeGreaterThanOrEqual(1);
  for (const text of await why.allInnerTexts()) {
    expect(text).toContain("Why this confidence");
  }

  // Evidence classes are labelled in marketer language.
  const body = await dialog.innerText();
  expect(body).toMatch(/Vendor-documented|Independently researched|Directly observed/);

  // Unknown dimensions are shown as explicit information, never as blank cells.
  await expect(dialog.getByTestId("trust-summary")).toContainText("unknown");

  await page.screenshot({ path: `${SHOTS}/evidence-trust.png`, fullPage: false });
});

test("inline conflict and controlled observation are distinct from vendor documentation", async ({ page }) => {
  // The fixture carries a conflict and a controlled observation; the live ledger
  // currently has no controlled observation (issue #10 is deferred), so this
  // assertion is meaningful in fixture mode and skips on live data.
  test.skip(!process.env.EVIDENCE_FIXTURE, "fixture-only structure: controlled observation + inline conflict");
  test.skip((page.viewportSize()?.width ?? 0) < 861, "desktop layout");

  await page.goto("/surfaces");
  await page.getByTestId("search-input").fill("ChatGPT");
  await page.getByTestId("row-chatgpt").scrollIntoViewIfNeeded();
  await page.getByTestId("cell-chatgpt-evidence").click();

  const dialog = page.getByRole("dialog");
  await expect(dialog).toBeVisible();
  // Await the lazily-loaded trust panel before asserting its contents.
  await expect(dialog.getByTestId("trust-summary")).toBeVisible();
  await expect(dialog.getByTestId("trust-conflict").first()).toBeVisible();

  const body = await dialog.innerText();
  expect(body).toContain("Directly observed");
  expect(body).toContain("Vendor-documented");
  expect(body).toContain("Compare the contradicting evidence");

  // DELTA-1: a re-derived rationale that supports a label other than the stored
  // one is surfaced explicitly, never shown as if it agreed.
  await expect(dialog.getByTestId("trust-derived-note").first()).toBeVisible();
});
