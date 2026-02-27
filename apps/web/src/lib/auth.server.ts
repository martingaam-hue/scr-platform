import { auth } from "@clerk/nextjs/server";

/**
 * Get Clerk token in server components / Route Handlers / Server Actions.
 * Import from "@/lib/auth.server" in server contexts only.
 */
export async function getServerToken(): Promise<string | null> {
  const { getToken } = await auth();
  return getToken();
}

/**
 * Server-side API call helper with automatic Clerk JWT.
 */
export async function serverFetch<T>(
  url: string,
  options: RequestInit = {}
): Promise<T> {
  const token = await getServerToken();
  const baseURL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

  const response = await fetch(`${baseURL}${url}`, {
    ...options,
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
      ...options.headers,
    },
  });

  if (!response.ok) {
    throw new Error(`API error: ${response.status} ${response.statusText}`);
  }

  return response.json() as Promise<T>;
}
