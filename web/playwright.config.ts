import { defineConfig, devices } from "@playwright/test";

/** Port for the product server, overridable so the suite never collides with a
 *  service already bound to the default (issue #45 ran into Grafana on 3000). */
const PORT = Number(process.env.WEB_PORT ?? 3000);
const BASE_URL = process.env.PLANE_BASE_URL ?? `http://127.0.0.1:${PORT}`;

export default defineConfig({
  testDir: "./e2e",
  timeout: 60_000,
  expect: { timeout: 10_000 },
  reporter: [["list"]],
  use: { trace: "off", baseURL: BASE_URL },
  webServer: {
    command: `npm start -- -p ${PORT}`,
    url: BASE_URL,
    reuseExistingServer: !process.env.CI,
    timeout: 30_000,
  },
  projects: [
    // PLAYWRIGHT_CHANNEL=chrome runs the suite against the system Chrome. Used on
    // hosts where Playwright's bundled chromium cannot be installed (e.g. macOS 12);
    // CI and default runs keep the bundled browser.
    { name: "desktop-chromium", use: { ...devices["Desktop Chrome"], ...(process.env.PLAYWRIGHT_CHANNEL ? { channel: process.env.PLAYWRIGHT_CHANNEL } : {}) } },
    { name: "mobile-chromium", use: { ...devices["Pixel 7"], ...(process.env.PLAYWRIGHT_CHANNEL ? { channel: process.env.PLAYWRIGHT_CHANNEL } : {}) } },
  ],
});
