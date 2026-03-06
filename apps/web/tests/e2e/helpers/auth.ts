import { type Page, expect } from "@playwright/test";

export const TEST_CREDENTIALS = {
  ally: {
    email: process.env.TEST_ALLY_EMAIL || "test-ally@scr-platform.test",
    password: process.env.TEST_ALLY_PASSWORD || "TestPass123!",
  },
  investor: {
    email: process.env.TEST_INVESTOR_EMAIL || "test-investor@scr-platform.test",
    password: process.env.TEST_INVESTOR_PASSWORD || "TestPass123!",
  },
  admin: {
    email: process.env.TEST_ADMIN_EMAIL || "test-admin@scr-platform.test",
    password: process.env.TEST_ADMIN_PASSWORD || "TestPass123!",
  },
};

/** Sign in using Clerk's multi-step embedded UI (email → Continue → password → Continue). */
async function clerkSignIn(
  page: Page,
  email: string,
  password: string,
): Promise<void> {
  await page.goto("/sign-in");

  // Step 1: email
  await page.getByLabel(/email address/i).fill(email);
  await page.getByRole("button", { name: /continue/i }).click();

  // Step 2: password (appears after email is accepted)
  await page.getByLabel(/^password$/i).fill(password);
  await page.getByRole("button", { name: /continue/i }).click();
}

export async function loginAsAlly(page: Page): Promise<void> {
  await clerkSignIn(page, TEST_CREDENTIALS.ally.email, TEST_CREDENTIALS.ally.password);
  await expect(page).toHaveURL(/\/(dashboard|projects|$)/);
}

export async function loginAsInvestor(page: Page): Promise<void> {
  await clerkSignIn(page, TEST_CREDENTIALS.investor.email, TEST_CREDENTIALS.investor.password);
  await expect(page).toHaveURL(/\/(dashboard|portfolio|$)/);
}

export async function loginAsAdmin(page: Page): Promise<void> {
  await clerkSignIn(page, TEST_CREDENTIALS.admin.email, TEST_CREDENTIALS.admin.password);
  await expect(page).toHaveURL(/\/(dashboard|admin|$)/);
}
