import { expect, test } from "@playwright/test";
import { draftFirstBid, finishOnboarding, register } from "./helpers";

test("approve a proposal: inbox -> draft -> studio -> approve -> submitted once", async ({ page }) => {
  await register(page); await finishOnboarding(page);
  await draftFirstBid(page);
  // evidence on hover/focus for a cited claim
  const cite = page.getByRole("button", { name: /Evidence \[E1\]/ }).first();
  await cite.focus();
  await expect(page.getByTestId("evidence-tooltip")).toBeVisible();
  await expect(page.getByText(/Dry-run preview/)).toBeVisible();
  await page.getByRole("button", { name: "Approve & send" }).click();
  await expect(page.getByTestId("submitted")).toBeVisible({ timeout: 60_000 });
  await page.goto("/pipeline");
  await expect(page.getByRole("region", { name: "submitted" }).or(page.getByRole("region", { name: "lost" })).first()).toBeVisible();
});
