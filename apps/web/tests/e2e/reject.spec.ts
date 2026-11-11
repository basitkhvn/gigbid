import { expect, test } from "@playwright/test";
import { draftFirstBid, finishOnboarding, register } from "./helpers";

test("reject with a reason: reason is required and is stored", async ({ page }) => {
  await register(page); await finishOnboarding(page);
  await draftFirstBid(page);
  await page.getByRole("button", { name: "Reject…" }).click();
  await expect(page.getByRole("button", { name: "Confirm reject" })).toBeDisabled();   // reason required
  await page.getByLabel("Reason (required)").fill("budget too low for the scope");
  await page.getByRole("button", { name: "Confirm reject" }).click();
  await expect(page.getByText("Rejected: budget too low for the scope")).toBeVisible({ timeout: 60_000 });
});
