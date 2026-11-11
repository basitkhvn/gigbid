import { expect, test } from "@playwright/test";
import { finishOnboarding, register } from "./helpers";

test("onboarding: register, connect GigSim, upload portfolio, set rates and budget", async ({ page }) => {
  await register(page);
  await page.getByRole("button", { name: /Connect GigSim/ }).click();
  await expect(page.getByText("GigSim connected")).toBeVisible();
  await page.getByLabel("Title").fill("E2E case study");
  await page.getByLabel(/Case study text/).fill("Built a retrieval pipeline with FastAPI for a logistics client, cutting search time by 40%.");
  await page.getByRole("button", { name: /Upload/ }).click();
  await expect(page.getByText(/Indexed ml-user-/)).toBeVisible();
  await page.getByLabel("Hourly rate (USD)").fill("62");
  await page.getByLabel("Weekly Connects budget").fill("90");
  await finishOnboarding(page);
  await page.goto("/settings");
  await expect(page.getByLabel("Hourly rate")).toHaveValue("62");
  await expect(page.getByLabel("Weekly Connects budget")).toHaveValue("90");
});
