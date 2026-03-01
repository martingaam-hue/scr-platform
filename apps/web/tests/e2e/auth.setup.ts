import { test as setup, expect } from "@playwright/test";
import { loginAsAlly } from "./helpers/auth";
import path from "path";

const authFile = path.join(__dirname, ".auth/user.json");

setup("authenticate", async ({ page }) => {
  await loginAsAlly(page);
  // Wait for the app to fully load
  await page.waitForLoadState("networkidle");
  // Save storage state (cookies, localStorage) for reuse across tests
  await page.context().storageState({ path: authFile });
});
