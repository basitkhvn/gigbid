// Windows variant of playwright.config.ts (the original uses POSIX paths: `rm -rf`, `.venv/bin/python`, /tmp).
// Run: npx playwright test -c playwright.win.config.ts
import { defineConfig, devices } from "@playwright/test";
import fs from "fs";
import os from "os";
import path from "path";

const ROOT = path.resolve(__dirname, "../..");
const PY = path.join(ROOT, ".venv", "Scripts", "python.exe");
const STATE = fs.mkdtempSync(path.join(os.tmpdir(), "gigbid-e2e-"));

export default defineConfig({
  testDir: "./tests/e2e",
  timeout: 90_000,
  expect: { timeout: 30_000 },
  workers: 1,
  reporter: [["list"], ["html", { outputFolder: "playwright-report", open: "never" }]],
  use: { baseURL: "http://localhost:3100", trace: "retain-on-failure", screenshot: "only-on-failure" },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: [
    {
      command: `"${PY}" -m uvicorn apps.api.main:app --port 8000`,
      cwd: ROOT, url: "http://localhost:8000/health", timeout: 180_000, reuseExistingServer: false,
      env: { PYTHONPATH: ROOT, MODEL_PROFILE: "offline", GIGBID_STATE_DIR: STATE, REVIEWER_PASSWORD: "e2e-reviewer-pass", GIGSIM_ERROR_RATE: "0", GIGSIM_INPROCESS: "1",
        CORS_ORIGINS: "http://localhost:3100", HF_HUB_DISABLE_TELEMETRY: "1" },
    },
    {
      command: "npx next dev -p 3100", cwd: __dirname, url: "http://localhost:3100/login", timeout: 180_000, reuseExistingServer: false,
      env: { NEXT_PUBLIC_API_URL: "http://localhost:8000" },
    },
  ],
});
