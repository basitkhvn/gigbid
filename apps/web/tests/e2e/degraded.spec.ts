import { expect, test } from "@playwright/test";
import { finishOnboarding, register } from "./helpers";

// Never leave the shared backend in outage mode for other specs, even when this test fails midway.
test.afterEach(async ({ page }) => {
  await page.evaluate(async () => {
    const t = localStorage.getItem("gigbid_token");
    if (t) await fetch("http://localhost:8000/admin/chaos/marketplace/up", { method: "POST", headers: { Authorization: `Bearer ${t}` } });
  }).catch(() => {});
});

test("degraded mode: banner appears when the marketplace is down and clears on recovery", async ({ page }) => {
  await register(page); await finishOnboarding(page);
  await expect(page.getByTestId("degraded-banner")).toHaveCount(0);
  const menu = page.getByRole("button", { name: "Menu" });
  if (await menu.isVisible()) await menu.click();   // phone layout only
  await page.getByTestId("chaos-toggle").click();
  await expect(page.getByTestId("degraded-banner")).toContainText("Marketplace unavailable — work is queued and will resume");
  await page.goto("/pipeline");
  await expect(page.getByTestId("degraded-banner")).toBeVisible();
  await page.getByTestId("chaos-toggle").click();
  await expect(page.getByTestId("degraded-banner")).toHaveCount(0, { timeout: 15_000 });
});
