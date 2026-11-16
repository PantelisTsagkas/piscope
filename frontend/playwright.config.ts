import { tmpdir } from "node:os";
import { join } from "node:path";

import { defineConfig, devices } from "@playwright/test";

/**
 * End-to-end tests run the real API against the real digits in ../data and a production
 * build of the frontend. Ports differ from the development defaults so a running dev
 * setup is left alone, and the experiment log goes to a temp file so the tests never
 * touch (or clear) a developer's own log.
 */
const API_PORT = 8100;
const WEB_PORT = 3100;
const API_ORIGIN = `http://127.0.0.1:${API_PORT}`;
const WEB_ORIGIN = `http://127.0.0.1:${WEB_PORT}`;
const EXPERIMENTS_FILE = join(tmpdir(), `piscope-e2e-experiments-${process.pid}.jsonl`);

export default defineConfig({
  testDir: "./tests/e2e",
  fullyParallel: true,
  forbidOnly: Boolean(process.env.CI),
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? [["github"], ["html", { open: "never" }]] : "list",
  use: {
    baseURL: WEB_ORIGIN,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  projects: [
    { name: "desktop", use: { ...devices["Desktop Chrome"] } },
    {
      name: "mobile",
      use: { ...devices["Pixel 7"] },
      // The narrow layout only needs its own navigation and overflow checks.
      testMatch: /responsive\.spec\.ts/,
    },
  ],
  webServer: [
    {
      command: `uv run uvicorn piscope_api.main:create_app --factory --host 127.0.0.1 --port ${API_PORT}`,
      cwd: "..",
      url: `${API_ORIGIN}/api/v1/health`,
      reuseExistingServer: false,
      env: {
        PISCOPE_DATA_DIR: "data",
        PISCOPE_EXPERIMENTS_FILE: EXPERIMENTS_FILE,
        PISCOPE_CORS_ORIGINS: JSON.stringify([WEB_ORIGIN]),
      },
    },
    {
      command: "pnpm build && pnpm start:standalone",
      url: WEB_ORIGIN,
      reuseExistingServer: false,
      timeout: 180_000,
      env: {
        NEXT_PUBLIC_API_URL: API_ORIGIN,
        PORT: String(WEB_PORT),
        HOSTNAME: "127.0.0.1",
      },
    },
  ],
});
