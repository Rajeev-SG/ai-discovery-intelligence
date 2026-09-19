import { expect, test } from "@playwright/test";
import { mkdirSync } from "node:fs";

const SHOTS = "proof";

/**
 * Live proof for issue #46 against the real read-only evidence API
 * (EVIDENCE_API_URL). Skips unless the API is configured so the suite stays
 * green in environments without production evidence.
 */
const HAS_API = Boolean(process.env.EVIDENCE_API_URL);

test.beforeAll(() => {
  mkdirSync(SHOTS, { recursive: true });
});

test("chatgpt drawer shows the real claim, value, source, provenance, confidence and history", async ({ page }) => {
  test.skip(!HAS_API, "requires EVIDENCE_API_URL");
  test.skip((page.viewportSize()?.width ?? 0) < 861, "desktop row path");

  await page.goto("/");
  await page.getByTestId("row-chatgpt").scrollIntoViewIfNeeded();
  await page.getByTestId("cell-chatgpt-evidence").click();

  const dialog = page.getByRole("dialog");
  await expect(dialog).toBeVisible();

  // Real claim statement + value + unit/scope.
  await expect(dialog.getByTestId("evidence-claims")).toBeVisible();
  await expect(dialog).toContainText("robots.txt");
  await expect(dialog).toContainText("24");

  // Public source link with the safe rel attributes.
  const link = dialog.locator('a[href="https://developers.openai.com/api/docs/bots"]').first();
  await expect(link).toBeVisible();
  await expect(link).toHaveAttribute("target", "_blank");
  await expect(link).toHaveAttribute("rel", /noreferrer noopener/);

  // Confidence is evidence-derived and inspectable.
  await expect(dialog).toContainText("confidence");

  // Expansion reveals provenance quote; no private filesystem path leaks.
  await dialog.locator("summary", { hasText: "Technical provenance" }).first().click();
  await expect(dialog).toContainText("For search results, please note it can take ~24 hours");
  await expect(dialog).toContainText("snapshot");
  await expect(dialog).not.toContainText("/var/");
  await expect(dialog).not.toContainText("/home/");

  await page.screenshot({ path: `${SHOTS}/evidence-chatgpt.png`, fullPage: false });
});

test("a no-evidence surface shows the explicit no-evidence state", async ({ page }) => {
  test.skip(!HAS_API, "requires EVIDENCE_API_URL");
  test.skip((page.viewportSize()?.width ?? 0) < 861, "desktop row path");

  await page.goto("/");
  await page.getByTestId("search-input").fill("DeepSeek");
  await page.getByTestId("row-deepseek-chat").scrollIntoViewIfNeeded();
  await page.getByTestId("cell-deepseek-chat-evidence").click();

  const dialog = page.getByRole("dialog");
  await expect(dialog).toBeVisible();
  await expect(dialog.getByTestId("no-evidence")).toBeVisible();
  await expect(dialog).toContainText("No evidence");

  await page.screenshot({ path: `${SHOTS}/evidence-no-evidence.png`, fullPage: false });
});
