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
  const phone = width === 390;
  await page.setViewportSize({ width, height: phone ? 844 : 900 });
  const errors = observeErrors(page);

  expect((await page.goto("/"))?.status()).toBe(200);
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(
    "Where brands show up in AI answers, shopping recommendations and ads.",
  );
  const nav = page.getByRole("navigation", { name: "AI surfaces" });
  // The site header is a second landmark; on a phone its links sit behind
  // the disclosure control, so it is asserted by name rather than by count.
  await expect(nav).toHaveCount(1);
  await expect(page.getByTestId("site-header").getByRole("link", { name: "Rajeev Gill" })).toHaveAttribute(
    "href",
    "https://rajeevg.com",
  );
  const picker = nav.getByLabel("AI surface", { exact: true });
  if (phone) {
    // Under 640px the pill wall is replaced by one native select.
    await expect(picker).toBeVisible();
    await expect(nav.getByRole("link")).toHaveCount(0);
    await expect(picker.locator("optgroup[label='Field guides'] option")).toHaveCount(guides.size);
  } else {
    await expect(picker).toBeHidden();
    await expect(nav.getByRole("link")).toHaveCount(guides.size);
  }
  await expect(page.locator('a[href^="/pov"], a[href^="/reconciliation"], a[href^="/implications"], a[href^="/landscape"]')).toHaveCount(0);
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBe(width);
  await page.screenshot({ path: testInfo.outputPath(`home-${width}.png`), fullPage: true, scale: "css" });

  for (const [slug, guide] of guides) {
    const route = `/surfaces/${slug}`;
    expect((await page.goto(route))?.status()).toBe(200);
    if (phone) {
      await expect(nav.getByLabel("AI surface", { exact: true })).toHaveValue(slug);
    } else {
      await expect(nav.locator(`a[href="${route}"]`)).toHaveCount(1);
      await expect(nav.locator(`a[href="${route}"]`)).toHaveAttribute("aria-current", "page");
    }
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
      const crawlers = guide.mechanics.find(({ label }) => label === "Crawlers");
      if (crawlers && "crawlers" in crawlers) {
        await expect(article.getByRole("table", { name: "Crawlers" }).getByRole("rowheader")).toHaveText(
          crawlers.crawlers.map(({ userAgent }) => userAgent),
        );
      }
      if (guide.mechanics.some((row) => "undocumented" in row)) {
        await expect(article.getByText(`Not documented by ${guide.vendor}.`, { exact: true }).first()).toBeVisible();
      }
      await page.screenshot({ path: testInfo.outputPath(`chatgpt-${width}.png`), fullPage: true, scale: "css" });
    }
  }

  expect(errors).toEqual([]);
});

test("visitors can open guides and see why some surfaces are coming soon", async ({ page }, testInfo) => {
  const phone = testInfo.project.name === "mobile-chromium";
  await page.goto("/");
  const nav = page.getByRole("navigation", { name: "AI surfaces" });

  if (phone) {
    // The compact control carries coming-soon surfaces as a disabled optgroup.
    const picker = nav.getByLabel("AI surface", { exact: true });
    const soon = picker.locator("optgroup[label='Coming soon'] option");
    await expect(soon.first()).toHaveCount(1);
    await expect(soon.first()).toBeDisabled();
    await picker.selectOption("perplexity");
    await expect(page).toHaveURL(/\/surfaces\/perplexity$/);
    await expect(page.getByRole("heading", { level: 1 })).toHaveText("Perplexity");
    await picker.selectOption("naver-ai");
    await expect(page).toHaveURL(/\/surfaces\/naver-ai$/);
    await expect(page.getByRole("heading", { level: 1 })).toHaveText("NAVER AI Tab");
    expect((await page.goto("/surfaces/not-in-the-directory"))?.status()).toBe(404);
    return;
  }

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

test("a phone gets one compact control and the guide heading stays above the fold", async ({ page }, testInfo) => {
  const phone = testInfo.project.name === "mobile-chromium";
  await page.setViewportSize({ width: phone ? 390 : 1440, height: 844 });
  await page.goto("/surfaces/chatgpt");

  const nav = page.getByRole("navigation", { name: "AI surfaces" });
  const picker = nav.getByLabel("AI surface", { exact: true });
  const heading = page.getByRole("heading", { level: 1 });

  if (phone) {
    await expect(picker).toBeVisible();
    await expect(nav.getByRole("link")).toHaveCount(0);
    // The regression this guards: pills used to consume the whole first screen.
    const switcher = await nav.boundingBox();
    const title = await heading.boundingBox();
    expect(switcher!.height).toBeLessThan(120);
    expect(title!.y).toBeLessThan(844 / 2);
  } else {
    await expect(picker).toBeHidden();
    expect(await nav.getByRole("link").count()).toBeGreaterThan(3);
    await expect(heading).toBeVisible();
  }
});

test("the rajeevg.com header frames the page at desktop and mobile widths", async ({ page }, testInfo) => {
  const width = testInfo.project.name === "mobile-chromium" ? 390 : 1440;
  await page.setViewportSize({ width, height: width === 390 ? 844 : 900 });
  await page.goto("/surfaces/chatgpt");

  const header = page.getByTestId("site-header");
  await expect(header).toBeVisible();
  await expect(header.getByRole("link", { name: "Rajeev Gill" })).toHaveAttribute(
    "href",
    "https://rajeevg.com",
  );

  const expected = [
    ["Home", "https://rajeevg.com/"],
    ["Solutions", "https://rajeevg.com/solutions"],
    ["Interfaces", "https://rajeevg.com/interfaces"],
    ["Writing", "https://rajeevg.com/blog"],
    ["About", "https://rajeevg.com/about"],
  ] as const;

  if (width === 390) {
    // The nav collapses behind the disclosure control on a phone.
    await expect(header.getByRole("navigation", { name: "Primary navigation" })).toBeHidden();
    await header.locator("summary").click();
    const mobile = header.getByRole("navigation", { name: "Mobile navigation" });
    for (const [name, href] of expected) {
      await expect(mobile.getByRole("link", { name })).toHaveAttribute("href", href);
    }
    await expect(mobile.getByRole("link", { name: "Solutions" })).toHaveAttribute(
      "aria-current",
      "page",
    );
  } else {
    const nav = header.getByRole("navigation", { name: "Primary navigation" });
    for (const [name, href] of expected) {
      await expect(nav.getByRole("link", { name, exact: true })).toHaveAttribute("href", href);
    }
    await expect(nav.getByRole("link", { name: "Solutions" })).toHaveAttribute(
      "aria-current",
      "page",
    );
  }

  // The header must not push the page sideways at either width.
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBe(width);
  await page.screenshot({
    path: testInfo.outputPath(`header-${width}.png`),
    clip: { x: 0, y: 0, width, height: 160 },
  });
});
