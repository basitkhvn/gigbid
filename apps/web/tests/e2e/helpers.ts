import { expect, Page } from "@playwright/test";

let n = 0;
/** Registers a brand-new user through the UI (tests are isolated: every test has its own user and data). */
export async function register(page: Page, persona = "ml") {
  const email = `e2e${Date.now()}${n++}@example.com`;
  await page.goto("/login");
  await page.getByRole("button", { name: "New here? Create an account" }).click();
  await page.getByLabel("Email").fill(email);
  await page.getByLabel(/Password/).fill("password-123");
  await page.getByLabel("Persona").selectOption(persona);
  await page.getByRole("button", { name: "Register" }).click();
  await expect(page).toHaveURL(/\/onboarding/);
  return email;
}

export async function finishOnboarding(page: Page) {
  await page.getByRole("button", { name: "Save and finish" }).click();
  await expect(page).toHaveURL(/localhost:3100\/$/);
}

/** Inbox -> Draft proposal on the first recommended job -> wait for the graph to pause at the approval interrupt -> open the studio. */
export async function draftFirstBid(page: Page) {
  const btn = page.getByRole("button", { name: "Draft proposal" }).first();
  await expect(btn).toBeVisible({ timeout: 60_000 });
  await btn.click();
  await expect(page).toHaveURL(/\/runs\//);
  await expect(page.getByText("awaiting_approval").first()).toBeVisible({ timeout: 60_000 });
  await page.getByRole("link", { name: "Open proposal studio" }).click();
  await expect(page).toHaveURL(/\/studio\//);
  await expect(page.getByRole("heading", { name: "Decision" })).toBeVisible();
}
