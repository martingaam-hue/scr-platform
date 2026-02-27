import axios from "axios";

export const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000",
  headers: {
    "Content-Type": "application/json",
  },
});

// Token injection is handled by setTokenProvider() in @/lib/auth.ts.
// Call useAuthenticatedApi() in a top-level client component to activate it.
// For server components, use serverFetch() from @/lib/auth.ts instead.

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Handle unauthorized — Clerk will redirect to sign-in
      if (typeof window !== "undefined") {
        window.location.href = "/sign-in";
      }
    }
    return Promise.reject(error);
  }
);
