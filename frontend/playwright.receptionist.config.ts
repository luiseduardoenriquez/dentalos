import { defineConfig } from "@playwright/test";

/**
 * Playwright config for receptionist E2E flows.
 * Runs headed (visible Chrome) against the live dev app on localhost:3000.
 *
 * Usage:
 *   npx playwright test --config=playwright.receptionist.config.ts
 *   npx playwright test --config=playwright.receptionist.config.ts tests/e2e/receptionist/18-33-full-day.spec.ts
 */
export default defineConfig({
  testDir: "./tests/e2e/receptionist",
  fullyParallel: false, // sequential — we want to watch
  retries: 0,
  workers: 1,
  timeout: 120_000, // 2 min per test (some flows are long)
  expect: { timeout: 10_000 },
  reporter: [["html", { open: "never" }], ["list"]],
  use: {
    baseURL: "http://localhost:3000",
    headless: false, // VISIBLE — so user can watch
    channel: "chrome", // Use real Google Chrome
    viewport: { width: 1440, height: 900 },
    actionTimeout: 15_000,
    navigationTimeout: 30_000,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
  },
  projects: [
    {
      name: "receptionist-flows",
      use: {
        storageState: "./tests/e2e/receptionist/.auth/receptionist.json",
      },
      dependencies: ["auth-setup"],
    },
    {
      name: "auth-setup",
      testMatch: /auth\.setup\.ts/,
    },
  ],
});
