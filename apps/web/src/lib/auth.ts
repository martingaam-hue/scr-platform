"use client";

import { useAuth as useClerkAuth } from "@clerk/nextjs";
import { useQuery } from "@tanstack/react-query";
import type { ComponentType } from "react";

import { api } from "@/lib/api";

// ── Types ───────────────────────────────────────────────────────────────

export type UserRole = "admin" | "manager" | "analyst" | "viewer";

export interface SCRUser {
  id: string;
  email: string;
  full_name: string;
  role: UserRole;
  org_id: string;
  org_name: string;
  org_type: "investor" | "ally" | "admin";
  org_slug: string;
  avatar_url: string | null;
  mfa_enabled: boolean;
  preferences: Record<string, unknown>;
  permissions: Record<string, string[]>; // resource_type -> actions[]
}

// ── Token Provider ──────────────────────────────────────────────────────

/**
 * Initialize the API client with Clerk token injection.
 * Call this once in a top-level client component (e.g. AuthProvider).
 */
export function useAuthenticatedApi() {
  const { getToken } = useClerkAuth();

  // Register the token provider so all api calls auto-include the JWT
  setTokenProvider(getToken);

  return api;
}

// Module-level token provider (set by useAuthenticatedApi)
let _getTokenFn: (() => Promise<string | null>) | null = null;
let _interceptorId: number | null = null;

export function setTokenProvider(fn: () => Promise<string | null>) {
  if (_getTokenFn === fn) return; // already set
  _getTokenFn = fn;

  // Remove previous interceptor if any
  if (_interceptorId !== null) {
    api.interceptors.request.eject(_interceptorId);
  }

  _interceptorId = api.interceptors.request.use(
    async (config) => {
      if (_getTokenFn) {
        const token = await _getTokenFn();
        if (token) {
          config.headers.Authorization = `Bearer ${token}`;
        }
      }
      return config;
    },
    (error) => Promise.reject(error)
  );
}

// ── Server-side helpers ─────────────────────────────────────────────────

/**
 * Get Clerk token in server components / Route Handlers / Server Actions.
 * Must be called in a server context only.
 */
export async function getServerToken(): Promise<string | null> {
  const { auth } = await import("@clerk/nextjs/server");
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

// ── Hooks ───────────────────────────────────────────────────────────────

/**
 * Primary auth hook for client components.
 * Fetches the full SCR user profile from our backend (not just Clerk data).
 */
export function useSCRUser() {
  const { isLoaded, isSignedIn, getToken } = useClerkAuth();

  const query = useQuery<SCRUser>({
    queryKey: ["auth", "me"],
    queryFn: async () => {
      const token = await getToken();
      const response = await api.get("/auth/me", {
        headers: { Authorization: `Bearer ${token}` },
      });
      return response.data;
    },
    enabled: isLoaded && !!isSignedIn,
    staleTime: 5 * 60 * 1000, // 5 min
    gcTime: 10 * 60 * 1000,
  });

  return {
    user: query.data ?? null,
    isLoaded: isLoaded && (query.isSuccess || query.isError),
    isSignedIn: isSignedIn ?? false,
    isLoading: query.isLoading,
    error: query.error,
    refetch: query.refetch,
  };
}

/**
 * Check if the current user has a specific permission.
 */
export function usePermission(action: string, resourceType: string): boolean {
  const { user } = useSCRUser();
  if (!user?.permissions) return false;
  const actions = user.permissions[resourceType];
  return actions?.includes(action) ?? false;
}

/**
 * Check multiple permissions at once.
 */
export function usePermissions(
  checks: Array<{ action: string; resourceType: string }>
): boolean[] {
  const { user } = useSCRUser();
  if (!user?.permissions) return checks.map(() => false);
  return checks.map(({ action, resourceType }) => {
    const actions = user.permissions[resourceType];
    return actions?.includes(action) ?? false;
  });
}

// ── HOC ─────────────────────────────────────────────────────────────────

/**
 * Higher-order component for role-based page protection.
 * Redirects to /dashboard if the user lacks the required role.
 */
export function withRole<P extends object>(
  Component: ComponentType<P>,
  allowedRoles: UserRole[]
) {
  return function ProtectedComponent(props: P) {
    const { user, isLoaded, isSignedIn } = useSCRUser();

    if (!isLoaded) return null;

    if (!isSignedIn) {
      if (typeof window !== "undefined") window.location.href = "/sign-in";
      return null;
    }

    if (user && !allowedRoles.includes(user.role)) {
      if (typeof window !== "undefined") window.location.href = "/dashboard";
      return null;
    }

    return <Component {...props} />;
  };
}
