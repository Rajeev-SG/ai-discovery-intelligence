import { expect, test, type Page } from "@playwright/test";
import { loadSurfaceGuides } from "../lib/surface-guides";

const guides = loadSurfaceGuides();

function observeErrors(page: Page) {
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  page.on("console", (message) => {
    if (message.type() === "error") errors.push(message.text());
  });
  return errors;
}

test("home and every published guide render with no backend dependency", async ({ page }, testInfo) => {
  const width = testInfo.project.name === "mobile-chromium" ? 390 : 1280;
  await page.setViewportSize({ width, height: width === 390 ? 844 : 900 });
  const errors = observeErrors(page);

  expect((await page.goto("/"))?.status()).toBe(200);
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(
    "Where brands show up in AI answers, shopping recommendations and ads.",
  );
  const nav = page.getByRole("navigation", { name: "AI surfaces" });
  await expect(page.getByRole("navigation")).toHaveCount(1);
  await expect(nav.getByRole("link")).toHaveCount(guides.size);
  await expect(page.locator('a[href^="/pov"], a[href^="/reconciliation"], a[href^="/implications"], a[href^="/landscape"]')).toHaveCount(0);
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBe(width);
  await page.screenshot({ path: testInfo.outputPath(`home-${width}.png`), fullPage: true, scale: "css" });

  for (const [slug, guide] of guides) {
    const route = `/surfaces/${slug}`;
    await expect(nav.locator(`a[href="${route}"]`)).toHaveCount(1);
    expect((await page.goto(route))?.status()).toBe(200);
    await expect(nav.locator(`a[href="${route}"]`)).toHaveAttribute("aria-current", "page");
    await expect(page.getByRole("heading", { level: 1 })).toHaveText(guide.name);
    await expect(page).toHaveTitle(`${guide.name} — AI Discovery Intelligence`);
    await expect(page.locator('meta[name="description"]')).toHaveAttribute("content", guide.summary);

    const article = page.getByRole("article");
    await expect(article.getByRole("heading", { level: 2 })).toHaveText([
      "What to do", "How it works", "Recent changes that matter", /^Sources · checked /,
    ]);
    await expect(article.getByRole("list").first().getByRole("listitem")).toHaveCount(guide.actions.length);
    await expect(article.getByRole("link")).toHaveCount(guide.sources.length);
    expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBe(width);

    if (slug === "chatgpt") {
      await expect(article.getByRole("table", { name: "Crawlers" }).getByRole("rowheader")).toHaveText([
        "OAI-SearchBot", "GPTBot", "ChatGPT-User", "OAI-AdsBot",
      ]);
      await expect(article.getByText("Not documented by OpenAI.", { exact: true })).toBeVisible();
      await page.screenshot({ path: testInfo.outputPath(`chatgpt-${width}.png`), fullPage: true, scale: "css" });
    }
  }

  expect(errors).toEqual([]);
});

test("visitors can open guides and see why some surfaces are coming soon", async ({ page }) => {
  await page.goto("/");
  const nav = page.getByRole("navigation", { name: "AI surfaces" });
  await nav.getByText("Coming soon", { exact: true }).click();
  await expect(nav.getByRole("listitem").first()).toBeVisible();
  await expect(nav.getByRole("listitem").first().locator("small")).not.toBeEmpty();
  await expect(nav.getByRole("listitem").first().getByRole("link")).toHaveCount(0);

  await nav.getByRole("link", { name: "Perplexity" }).click();
  await expect(page).toHaveURL(/\/surfaces\/perplexity$/);
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Perplexity");

  await nav.getByRole("link", { name: "NAVER AI Tab" }).click();
  await expect(page).toHaveURL(/\/surfaces\/naver-ai$/);
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("NAVER AI Tab");
  expect((await page.goto("/surfaces/not-in-the-directory"))?.status()).toBe(404);
});
