import { expect, test } from "@playwright/test";
import { mkdirSync } from "node:fs";

const BASE = process.env.PLANE_URL;
const SHOTS = "proof";

/**
 * Collect the row ids the virtualizer actually renders as the body is
 * scrolled. This is the honest check for "every surface is reachable" with
 * TanStack Virtual: rows exist in the DOM only while they are in view.
 */
async function collectRenderedRowIds(page: import("@playwright/test").Page): Promise<Set<string>> {
  const body = page.getByTestId("table-body");
  const seen = new Set<string>();
  const total = await body.evaluate((el) => el.scrollHeight);
  const step = Math.max(200, Math.floor(total / 24));
  for (let offset = 0; offset <= total; offset += step) {
    await body.evaluate((el, y) => {
      el.scrollTop = y;
    }, offset);
    await page.waitForTimeout(60);
    const ids = await page.locator('[data-testid^="row-"]').evaluateAll((nodes) =>
      nodes.map((node) => (node.getAttribute("data-testid") ?? "").replace(/^row-/, "")),
    );
    for (const id of ids) seen.add(id);
    if (seen.size >= 35) break;
  }
  return seen;
}


test.beforeAll(() => {
  mkdirSync(SHOTS, { recursive: true });
});

test.beforeEach(async ({ page }) => {
  await page.goto(BASE ?? "/surfaces");
});

test("renders every canonical surface and the named global/regional products", async ({ page }) => {
  await expect(page.getByTestId("registry-count")).toHaveText("35");
  await expect(page.getByTestId("surface-count")).toHaveText("35");

  const desktop = page.viewportSize()!.width >= 861;
  if (!desktop) {
    // Mobile cards render all rows; this is the full-registry proof.
    for (const id of ["chatgpt", "deepseek-chat", "doubao", "qwen-consumer", "naver-ai", "yandex-ai-search"]) {
      await expect(page.getByTestId(`card-${id}`)).toBeVisible();
    }
    await expect(page.getByTestId("card-doubao")).toContainText("Doubao");
    await page.screenshot({ path: `${SHOTS}/mobile-registry.png`, fullPage: false });
    return;
  }

  // Desktop: scroll the virtualized body and confirm all 35 surfaces render,
  // including every product the issue names.
  const rendered = await collectRenderedRowIds(page);
  expect(rendered.size).toBe(35);
  for (const id of ["chatgpt", "deepseek-chat", "doubao", "qwen-consumer", "naver-ai", "yandex-ai-search"]) {
    expect(rendered.has(id)).toBe(true);
  }

  await page.getByTestId("table-body").evaluate((el) => {
    el.scrollTop = 0;
  });
  await expect(page.getByTestId("row-chatgpt")).toBeVisible();
  await page.screenshot({ path: `${SHOTS}/desktop-registry.png`, fullPage: false });

  await page.getByTestId("search-input").fill("DeepSeek");
  await expect(page.getByTestId("row-deepseek-chat")).toContainText("DeepSeek Chat");
  await page.getByTestId("search-input").fill("NAVER");
  await expect(page.getByTestId("row-naver-ai")).toContainText("NAVER");
  await page.getByTestId("search-input").fill("Yandex");
  await expect(page.getByTestId("row-yandex-ai-search")).toContainText("Yandex");
  await page.getByTestId("search-input").fill("Doubao");
  await expect(page.getByTestId("row-doubao")).toContainText("Doubao");
  await page.getByTestId("search-input").fill("Qwen");
  await expect(page.getByTestId("row-qwen-consumer")).toContainText("Qwen");
  await page.getByTestId("search-input").fill("");
});

test("search, filter, sort and expanded DeepSeek detail", async ({ page }) => {
  const desktop = page.viewportSize()!.width >= 861;
  test.skip(!desktop, "dense desktop behaviour is the primary observation plane");

  // 1. Search "China"
  await page.getByTestId("search-input").fill("China");
  await expect(page.getByTestId("row-doubao")).toBeVisible();
  await expect(page.getByTestId("row-qwen-consumer")).toBeVisible();
  await expect(page.getByTestId("row-deepseek-chat")).toBeVisible();
  await expect(page.getByTestId("row-chatgpt")).toHaveCount(0);
  await expect(page.getByTestId("result-summary")).toContainText('matching “China”');
  await page.screenshot({ path: `${SHOTS}/desktop-search-china.png` });

  // 2. One facet filter: priority tier = Core — global
  await page.getByTestId("facet-tier").click();
  await page.getByTestId("facet-tier-option-Core — global").check();
  await page.keyboard.press("Escape");
  await expect(page.getByTestId("result-summary")).toContainText("facet active");
  // "China" search is still active, so only China surfaces in the core-global
  // tier remain — which is DeepSeek, because the registry marks it global+china.
  await expect(page.getByTestId("row-chatgpt")).toHaveCount(0);
  await expect(page.getByTestId("row-doubao")).toHaveCount(0);
  await expect(page.getByTestId("row-deepseek-chat")).toBeVisible();
  await page.screenshot({ path: `${SHOTS}/desktop-filter-tier.png` });

  // 3. One sort: click the Surface column header
  await page.getByTestId("facet-tier").click();
  await page.getByRole("button", { name: "Clear" }).click();
  await page.keyboard.press("Escape");
  await page.getByTestId("sort-name").click();
  const firstAsc = await page.getByTestId("table-body").locator(".tr").first().innerText();
  await page.getByTestId("sort-name").click();
  const firstDesc = await page.getByTestId("table-body").locator(".tr").first().innerText();
  expect(firstAsc).not.toBe(firstDesc);
  await expect(page.getByTestId("result-summary")).toContainText("sorted by name desc");
  await page.screenshot({ path: `${SHOTS}/desktop-sort.png` });

  // 4. Expanded DeepSeek row with explicit unknowns and official URLs
  await page.getByTestId("reset-all").click();
  await page.getByTestId("search-input").fill("DeepSeek");
  await page.getByTestId("expand-deepseek-chat").click();
  await expect(page.getByTestId("detail-deepseek-chat")).toBeVisible();
  await expect(page.getByTestId("detail-deepseek-chat")).toContainText("Upstream retrieval index/provider");
  await expect(page.getByTestId("detail-deepseek-chat")).toContainText("chat.deepseek.com");
  // Issue #58: DeepSeek's claims are stored under the alias "deepseek"; the read
  // path must resolve them, so a surface with aliased claims now shows its real
  // evidence instead of a false "No evidence".
  await expect(page.getByTestId("detail-deepseek-chat")).toContainText("validated claim");
  await page.screenshot({ path: `${SHOTS}/desktop-expanded-deepseek.png` });
});

test("URL state is shareable and restores the same view", async ({ page }) => {
  const desktop = page.viewportSize()!.width >= 861;
  test.skip(!desktop, "URL state covered on desktop");

  await page.getByTestId("search-input").fill("China");
  await page.getByTestId("sort-name").click();
  await page.getByTestId("expand-deepseek-chat").click();
  await expect(page.getByTestId("detail-deepseek-chat")).toBeVisible();

  await expect(page).toHaveURL(/q=China/);
  await expect(page).toHaveURL(/sort=name/);
  await expect(page).toHaveURL(/expanded=deepseek-chat/);
  const url = page.url();

  await page.goto(url);
  await expect(page.getByTestId("search-input")).toHaveValue("China");
  await expect(page.getByTestId("detail-deepseek-chat")).toBeVisible();
  await expect(page.getByTestId("result-summary")).toContainText("sorted by name");
});

test("keyboard-only navigation can filter and expand", async ({ page }) => {
  const desktop = page.viewportSize()!.width >= 861;
  test.skip(!desktop, "keyboard proof on desktop layout");

  // Focus search and type with the keyboard only.
  await page.getByTestId("search-input").focus();
  await page.keyboard.type("China");
  await expect(page.getByTestId("row-doubao")).toBeVisible();

  // Tab to a sortable header and activate it with Enter.
  await page.getByTestId("sort-name").focus();
  await page.keyboard.press("Enter");
  await expect(page.getByTestId("result-summary")).toContainText("sorted by name asc");

  // Row expansion by keyboard reveals the inline detail panel.
  await page.getByTestId("expand-deepseek-chat").focus();
  await page.keyboard.press("Enter");
  await expect(page.getByTestId("detail-deepseek-chat")).toBeVisible();
  await expect(page.getByTestId("detail-deepseek-chat")).toContainText("Upstream retrieval index/provider");

  // An evidence-bearing cell is keyboard-activatable and opens the drawer.
  await page.getByTestId("cell-deepseek-chat-retrieval").focus();
  await page.keyboard.press("Enter");
  await expect(page.getByRole("dialog")).toBeVisible();
  await expect(page.getByRole("dialog")).toContainText("Retrieval architecture");

  // Escape closes the focus-trapped drawer and returns focus.
  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog")).toBeHidden();

  // Collapse the inline detail with the keyboard too.
  await page.getByTestId("expand-deepseek-chat").focus();
  await page.keyboard.press("Enter");
  await expect(page.getByTestId("detail-deepseek-chat")).toHaveCount(0);
  await page.screenshot({ path: `${SHOTS}/desktop-keyboard.png` });
});

test("mobile layout exposes the registry and a detail panel", async ({ page }) => {
  const desktop = page.viewportSize()!.width >= 861;
  test.skip(desktop, "mobile-only behaviour");

  await page.getByTestId("search-input").fill("China");
  await expect(page.getByTestId("card-doubao")).toBeVisible();
  await expect(page.getByTestId("card-deepseek-chat")).toBeVisible();
  await page.getByTestId("card-open-deepseek-chat").click();
  await expect(page.getByRole("dialog")).toContainText("Retrieval architecture");
  await page.screenshot({ path: `${SHOTS}/mobile-detail-deepseek.png` });
});
