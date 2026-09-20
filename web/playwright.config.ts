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
    { name: "desktop-chromium", use: { ...devices["Desktop Chrome"] } },
    { name: "mobile-chromium", use: { ...devices["Pixel 7"] } },
  ],
});
