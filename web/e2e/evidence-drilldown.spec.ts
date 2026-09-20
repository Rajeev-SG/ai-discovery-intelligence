import { expect, test } from "@playwright/test";
import { mkdirSync } from "node:fs";

const SHOTS = "proof";

/**
 * Structural proof for issue #46. Assertions are structural (testids, presence
 * of non-empty values/quotes, link href origin) rather than brittle literals,
 * so the drawer contract is verified without depending on exact backend text.
 *
 * - `EVIDENCE_API_URL` set  -> runs against the live read-only API.
 * - `EVIDENCE_FIXTURE=1`    -> runs against recorded fixtures (works offline/CI).
 * One mode is always active in the job that owns this suite; both must be
 * configured there, so these tests never silently no-op.
 */
const HAS_API = Boolean(process.env.EVIDENCE_API_URL || process.env.EVIDENCE_FIXTURE);
const DESKTOP_ONLY = "server row path is the desktop layout";

test.beforeAll(() => {
  mkdirSync(SHOTS, { recursive: true });
});

test("evidenced surface: every claim, value, source link, provenance and confidence", async ({ page }) => {
  test.skip(!HAS_API, "requires EVIDENCE_API_URL or EVIDENCE_FIXTURE=1");
  test.skip((page.viewportSize()?.width ?? 0) < 861, DESKTOP_ONLY);

  await page.goto("/surfaces");
  await page.getByTestId("search-input").fill("ChatGPT");
  await page.getByTestId("row-chatgpt").scrollIntoViewIfNeeded();
  await page.getByTestId("cell-chatgpt-evidence").click();

  const dialog = page.getByRole("dialog");
  await expect(dialog).toBeVisible();

  // Detail is loaded lazily on drawer open; await it before asserting.
  const claims = dialog.getByTestId("evidence-claims").locator("> li");
  await expect(claims.first()).toBeVisible();
  expect(await claims.count()).toBeGreaterThanOrEqual(1);

  // At least one non-empty, non-"Unknown" value is shown.
  const values = dialog.getByTestId("evidence-value");
  expect(await values.count()).toBeGreaterThanOrEqual(1);
  const valueTexts = await values.locator(".evidence-value-num").allInnerTexts();
  expect(valueTexts.some((text) => text.trim() && text.trim() !== "Unknown")).toBe(true);

  // Public source link: present, opens in a new tab, no referrer.
  const sourceLink = dialog.locator(".evidence-grid a").first();
  await expect(sourceLink).toBeVisible();
  await expect(sourceLink).toHaveAttribute("target", "_blank");
  await expect(sourceLink).toHaveAttribute("rel", /noreferrer noopener/);
  const href = await sourceLink.getAttribute("href");
  expect(href).toMatch(/^https?:\/\//);

  // Confidence is visible in the concise view and in the technical detail.
  await expect(dialog).toContainText("confidence");

  // Expansion reveals a non-empty provenance quote and capture availability.
  await dialog.locator("summary", { hasText: "Technical provenance" }).first().click();
  const quote = dialog.getByTestId("provenance-quote").first();
  await expect(quote).toBeVisible();
  expect((await quote.innerText()).trim().length).toBeGreaterThan(0);
  await expect(dialog).toContainText("snapshot");
  // Never leak a private filesystem path.
  await expect(dialog).not.toContainText("/var/");
  await expect(dialog).not.toContainText("/home/");

  await page.screenshot({ path: `${SHOTS}/evidence-chatgpt.png`, fullPage: false });
});

test("no-evidence surface: explicit state, no contradictory chrome", async ({ page }) => {
  test.skip(!HAS_API, "requires EVIDENCE_API_URL or EVIDENCE_FIXTURE=1");
  test.skip((page.viewportSize()?.width ?? 0) < 861, DESKTOP_ONLY);

  await page.goto("/surfaces");
  await page.getByTestId("search-input").fill("DeepSeek");
  await page.getByTestId("row-deepseek-chat").scrollIntoViewIfNeeded();
  await page.getByTestId("cell-deepseek-chat-evidence").click();

  const dialog = page.getByRole("dialog");
  await expect(dialog).toBeVisible();
  await expect(dialog.getByTestId("no-evidence")).toBeVisible();
  // A bare no-evidence surface must not render an empty History block.
  await expect(dialog.getByTestId("evidence-history")).toHaveCount(0);

  await page.screenshot({ path: `${SHOTS}/evidence-no-evidence.png`, fullPage: false });
});
