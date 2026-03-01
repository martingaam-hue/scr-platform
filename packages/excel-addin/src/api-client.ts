/**
 * Thin HTTP client for the SCR Platform Excel API.
 *
 * The API key is stored in Office roaming settings so it persists across
 * sessions without ever touching the worksheet content.
 */

const SCR_API_URL = (process.env.SCR_API_URL as string) || "https://api.scrplatform.com";

/** Response shape returned by every /excel/* endpoint. */
export interface ExcelResponse {
  value: number | null;
  label: string;
  as_of: string | null;
  error?: string;
}

function getApiKey(): string {
  return (window as any).Office?.context?.roamingSettings?.get("scrApiKey") || "";
}

/**
 * Fetch a single /excel/* endpoint and return its parsed JSON.
 *
 * Throws with a user-friendly message on network errors, non-OK HTTP
 * responses, or when no API key has been configured.
 */
export async function fetchExcelEndpoint(path: string): Promise<ExcelResponse> {
  const apiKey = getApiKey();
  if (!apiKey) {
    throw new Error("SCR API key not configured. Open the task pane to set up.");
  }

  const response = await fetch(`${SCR_API_URL}${path}`, {
    headers: {
      "X-SCR-API-Key": apiKey,
      "Content-Type": "application/json",
    },
  });

  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error((err as any).detail || `SCR API error: ${response.status}`);
  }

  return response.json() as Promise<ExcelResponse>;
}

/**
 * Test whether a given API key is accepted by the platform.
 *
 * Uses the public /health endpoint so no data is exposed; the key is still
 * sent as a header so the server can validate it.
 */
export async function testConnection(apiKey: string): Promise<boolean> {
  try {
    const response = await fetch(`${SCR_API_URL}/health`, {
      headers: { "X-SCR-API-Key": apiKey },
    });
    return response.ok;
  } catch {
    return false;
  }
}
