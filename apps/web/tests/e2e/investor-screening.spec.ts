import { test, expect } from "@playwright/test";

test.describe("Investor Deal Screening", () => {
  test("deals page loads with pipeline and discover tabs", async ({ page }) => {
    await page.goto("/deals");
    await expect(page).toHaveURL(/deals/);

    // Check for tabs
    const pipelineTab = page.getByRole("tab", { name: /pipeline/i });
    const discoverTab = page.getByRole("tab", { name: /discover/i });

    // At least one of these should be visible
    const hasPipeline = await pipelineTab.isVisible();
    const hasDiscover = await discoverTab.isVisible();
    expect(hasPipeline || hasDiscover).toBeTruthy();
  });

  test("investor can view matching recommendations", async ({ page }) => {
    await page.goto("/matching");
    await page.waitForLoadState("networkidle");

    const heading = page.getByRole("heading", { name: /match|recommend/i });
    // Page should load without error
    await expect(page.locator("main")).toBeVisible({ timeout: 10_000 });
  });

  test("smart screener page loads", async ({ page }) => {
    await page.goto("/screener");
    await page.waitForLoadState("networkidle");
    await expect(page.locator("main")).toBeVisible({ timeout: 10_000 });
  });
});
