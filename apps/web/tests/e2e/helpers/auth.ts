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

export async function loginAsAlly(page: Page): Promise<void> {
  await page.goto("/sign-in");
  await page.getByLabel(/email/i).fill(TEST_CREDENTIALS.ally.email);
  await page.getByLabel(/password/i).fill(TEST_CREDENTIALS.ally.password);
  await page.getByRole("button", { name: /sign in|log in/i }).click();
  await expect(page).toHaveURL(/\/(dashboard|projects|$)/);
}

export async function loginAsInvestor(page: Page): Promise<void> {
  await page.goto("/sign-in");
  await page.getByLabel(/email/i).fill(TEST_CREDENTIALS.investor.email);
  await page.getByLabel(/password/i).fill(TEST_CREDENTIALS.investor.password);
  await page.getByRole("button", { name: /sign in|log in/i }).click();
  await expect(page).toHaveURL(/\/(dashboard|portfolio|$)/);
}

export async function loginAsAdmin(page: Page): Promise<void> {
  await page.goto("/sign-in");
  await page.getByLabel(/email/i).fill(TEST_CREDENTIALS.admin.email);
  await page.getByLabel(/password/i).fill(TEST_CREDENTIALS.admin.password);
  await page.getByRole("button", { name: /sign in|log in/i }).click();
  await expect(page).toHaveURL(/\/(dashboard|admin|$)/);
}
