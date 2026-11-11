import { expect, test } from "@playwright/test";
import { draftFirstBid, finishOnboarding, register } from "./helpers";

test("edit a draft then approve: the edit is what gets submitted", async ({ page }) => {
  await register(page); await finishOnboarding(page);
  await draftFirstBid(page);
  const editor = page.getByLabel("Cover letter editor");
  const marker = "I can share a short written plan before we start.";
  await editor.fill((await editor.inputValue()) + " " + marker);
  await page.getByRole("button", { name: "Save edit & approve" }).click();
  await expect(page.getByTestId("submitted")).toBeVisible({ timeout: 60_000 });
  await expect(page.getByTestId("draft-preview")).toContainText(marker);
});
