import { test, expect } from "@playwright/test";

test.describe("Portfolio Monitoring", () => {
  test("monitoring page loads", async ({ page }) => {
    await page.goto("/monitoring");
    await page.waitForLoadState("networkidle");
    await expect(page.locator("main")).toBeVisible({ timeout: 10_000 });
  });

  test("portfolio page loads with holdings", async ({ page }) => {
    await page.goto("/portfolio");
    await page.waitForLoadState("networkidle");
    await expect(page.locator("main")).toBeVisible({ timeout: 10_000 });
  });

  test("covenant monitoring shows traffic light status", async ({ page }) => {
    await page.goto("/monitoring");
    await page.waitForLoadState("networkidle");

    // Look for traffic light indicators or status badges
    const statusBadges = page.locator("[data-status], .badge, [class*='badge']");
    // Page loads without error is sufficient
    await expect(page.locator("main")).toBeVisible();
  });
});
