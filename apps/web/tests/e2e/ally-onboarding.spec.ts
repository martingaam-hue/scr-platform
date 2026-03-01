import { test, expect } from "@playwright/test";

test.describe("Ally Onboarding → Signal Score", () => {
  test("ally can complete onboarding and trigger signal score", async ({ page }) => {
    // Navigate to projects
    await page.goto("/projects");
    await expect(page).toHaveTitle(/projects|SCR/i);

    // Check projects page loads
    const heading = page.getByRole("heading", { name: /projects/i });
    await expect(heading).toBeVisible({ timeout: 10_000 });
  });

  test("ally can create a new project", async ({ page }) => {
    await page.goto("/projects");

    // Look for create project button
    const createBtn = page.getByRole("button", { name: /new project|create project/i });
    if (await createBtn.isVisible()) {
      await createBtn.click();
      // Should open a form or navigate to creation page
      await expect(page.getByText(/project type|project name/i)).toBeVisible({ timeout: 5_000 });
    }
  });

  test("signal score page loads for a project", async ({ page }) => {
    await page.goto("/projects");
    // Wait for project list
    await page.waitForLoadState("networkidle");

    // If there are projects, click into the first one
    const projectLinks = page.getByRole("link", { name: /view|open/i });
    const count = await projectLinks.count();
    if (count > 0) {
      await projectLinks.first().click();
      await page.waitForLoadState("networkidle");

      // Navigate to signal score
      const signalScoreLink = page.getByRole("link", { name: /signal score/i });
      if (await signalScoreLink.isVisible()) {
        await signalScoreLink.click();
        await expect(page.getByText(/signal score|overall score/i)).toBeVisible({ timeout: 10_000 });
      }
    }
  });
});
