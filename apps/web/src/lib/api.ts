import axios from "axios";

const _apiBase = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export const api = axios.create({
  baseURL: `${_apiBase}/v1`,
  headers: {
    "Content-Type": "application/json",
  },
});

// Token injection is handled by setTokenProvider() in @/lib/auth.ts.
// Call useAuthenticatedApi() in a top-level client component to activate it.
// For server components, use serverFetch() from @/lib/auth.server instead.

api.interceptors.response.use(
  (response) => response,
  (error) => Promise.reject(error)
);
