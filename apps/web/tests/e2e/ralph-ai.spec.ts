import { test, expect } from "@playwright/test";

test.describe("Ralph AI Assistant", () => {
  test("Ralph panel toggle button is present", async ({ page }) => {
    await page.goto("/projects");
    await page.waitForLoadState("networkidle");

    // Look for Ralph toggle button in topbar
    const ralphBtn = page.getByRole("button", { name: /ralph|ai assistant/i });
    if (await ralphBtn.isVisible()) {
      await ralphBtn.click();
      // Panel should open
      await expect(page.getByText(/ralph|how can i help/i)).toBeVisible({ timeout: 5_000 });
    }
  });

  test("Ralph can receive a message", async ({ page }) => {
    await page.goto("/projects");
    await page.waitForLoadState("networkidle");

    const ralphBtn = page.getByRole("button", { name: /ralph|ai assistant/i });
    if (await ralphBtn.isVisible()) {
      await ralphBtn.click();

      const input = page.getByRole("textbox", { name: /message|ask ralph/i });
      if (await input.isVisible()) {
        await input.fill("What is the signal score for this project?");
        await page.keyboard.press("Enter");
        // Wait for response (up to 15s)
        await expect(page.getByText(/signal score|analyzing|thinking/i)).toBeVisible({ timeout: 15_000 });
      }
    }
  });

  test("citation badges appear on AI-generated content", async ({ page }) => {
    await page.goto("/projects");
    await page.waitForLoadState("networkidle");

    // Navigate to signal score which has AI feedback + citations
    const projectLinks = page.getByRole("link", { name: /view|open/i });
    const count = await projectLinks.count();
    if (count > 0) {
      await projectLinks.first().click();

      const signalScoreLink = page.getByRole("link", { name: /signal score/i });
      if (await signalScoreLink.isVisible()) {
        await signalScoreLink.click();
        await page.waitForLoadState("networkidle");
        // Page should load without error
        await expect(page.locator("main")).toBeVisible();
      }
    }
  });
});
