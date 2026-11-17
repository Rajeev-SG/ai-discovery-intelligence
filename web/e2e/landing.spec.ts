import { expect, test, type Page } from "@playwright/test";

function observeErrors(page: Page) {
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  page.on("console", (message) => {
    if (message.type() === "error") errors.push(message.text());
  });
  return errors;
}

test("home and ChatGPT profile render the field guide with no backend dependency", async ({ page }, testInfo) => {
  const width = testInfo.project.name === "mobile-chromium" ? 390 : 1280;
  await page.setViewportSize({ width, height: width === 390 ? 844 : 900 });
  const errors = observeErrors(page);

  for (const [route, screenshot] of [
    ["/", "home"],
    ["/surfaces/chatgpt", "chatgpt"],
  ]) {
    const response = await page.goto(route);
    expect(response?.status()).toBe(200);
    const nav = page.getByRole("navigation", { name: "AI surfaces" });
    await expect(page.getByRole("navigation")).toHaveCount(1);
    await expect(nav.getByRole("link", { name: "ChatGPT" })).toHaveAttribute("aria-current", "page");

    const article = page.getByRole("article");
    await expect(article.getByRole("heading", { level: 1 })).toHaveText("ChatGPT");
    await expect(article.getByRole("heading", { level: 2 })).toHaveText([
      "What to do", "How it works", "Recent changes that matter", "Sources · checked 17 Nov 2026",
    ]);
    await expect(article.getByRole("list").first().getByRole("listitem")).toHaveCount(4);
    await expect(article.getByText("Not documented by OpenAI.", { exact: true })).toBeVisible();
    await expect(article.getByRole("table", { name: "Crawlers" }).getByRole("rowheader")).toHaveText([
      "OAI-SearchBot", "GPTBot", "ChatGPT-User", "OAI-AdsBot",
    ]);
    await expect(article.getByRole("link", { name: "OpenAI — Overview of OpenAI crawlers" }))
      .toHaveAttribute("href", "https://developers.openai.com/api/docs/bots");
    await expect(article.getByRole("link")).toHaveCount(5);

    expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBe(width);
    await page.screenshot({ path: testInfo.outputPath(`${screenshot}-${width}.png`), fullPage: true, scale: "css" });
  }

  expect(errors).toEqual([]);
});

test("the switcher opens published guides and lists upcoming surfaces without dead links", async ({ page }) => {
  await page.goto("/");
  const nav = page.getByRole("navigation", { name: "AI surfaces" });
  await expect(nav.getByText("Perplexity Coming soon")).toBeVisible();
  await expect(nav.getByRole("link", { name: "Perplexity" })).toHaveCount(0);
  await nav.getByText("More…", { exact: true }).click();
  await expect(nav.getByText("Yandex Search with Alice AI Coming soon")).toBeVisible();

  await nav.getByRole("link", { name: "Google AI Overviews & AI Mode" }).click();
  await expect(page).toHaveURL(/\/surfaces\/google-ai-search$/);
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Google AI Overviews & AI Mode");

  await nav.getByRole("link", { name: "NAVER AI Tab" }).click();
  await expect(page).toHaveURL(/\/surfaces\/naver-ai$/);
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("NAVER AI Tab");

  await nav.getByRole("link", { name: "ChatGPT" }).click();
  await expect(page).toHaveURL(/\/surfaces\/chatgpt$/);
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("ChatGPT");
  expect((await page.goto("/surfaces/perplexity"))?.status()).toBe(404);
});
