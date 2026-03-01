/**
 * Test seed helpers — call API endpoints to set up test data.
 * Uses the API directly (not the UI) for speed.
 */
import { type APIRequestContext } from "@playwright/test";

const API_BASE = process.env.PLAYWRIGHT_API_URL || "http://localhost:8000";

export async function createTestProject(
  request: APIRequestContext,
  authToken: string,
  data: Partial<{
    name: string;
    project_type: string;
    stage: string;
  }> = {}
): Promise<{ id: string; name: string }> {
  const response = await request.post(`${API_BASE}/projects`, {
    headers: { Authorization: `Bearer ${authToken}` },
    data: {
      name: data.name ?? `Test Project ${Date.now()}`,
      project_type: data.project_type ?? "solar",
      stage: data.stage ?? "development",
      description: "Playwright test project",
    },
  });
  return await response.json();
}

export async function getAuthToken(
  request: APIRequestContext,
  email: string,
  password: string
): Promise<string> {
  // In a real Clerk setup, tokens come from Clerk. For test environments,
  // use a test token endpoint or environment variable.
  return process.env.TEST_API_TOKEN ?? "test-token";
}
