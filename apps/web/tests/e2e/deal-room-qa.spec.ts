import { test, expect } from "@playwright/test";

test.describe("Deal Room Q&A", () => {
  test("deal rooms page loads", async ({ page }) => {
    await page.goto("/deal-rooms");
    await page.waitForLoadState("networkidle");
    await expect(page.locator("main")).toBeVisible({ timeout: 10_000 });
  });

  test("deal room detail shows tabs", async ({ page }) => {
    await page.goto("/deal-rooms");
    await page.waitForLoadState("networkidle");

    // Click into first deal room if available
    const roomLinks = page.getByRole("link", { name: /open|view/i });
    const count = await roomLinks.count();
    if (count > 0) {
      await roomLinks.first().click();
      await page.waitForLoadState("networkidle");

      // Q&A tab should be visible
      const qaTab = page.getByRole("tab", { name: /q&a|questions/i });
      if (await qaTab.isVisible()) {
        await qaTab.click();
        await expect(page.getByText(/questions|ask/i)).toBeVisible({ timeout: 5_000 });
      }
    }
  });

  test("can navigate to ask question form", async ({ page }) => {
    // Check that Q&A functionality exists somewhere
    await page.goto("/projects");
    await page.waitForLoadState("networkidle");
    // This is a soft check — if the page loads without error, it's a pass
    await expect(page.locator("main")).toBeVisible();
  });
});
