/**
 * Tests for the withRole HOC in lib/auth.tsx.
 *
 * withRole wraps a component and guards it by role:
 * - isLoaded=false  → renders nothing (null)
 * - not signed in   → redirects to /sign-in
 * - wrong role      → redirects to /dashboard
 * - correct role    → renders the wrapped component
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import React from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

// Mock Clerk before importing auth.tsx
vi.mock("@clerk/nextjs", () => ({
  useAuth: vi.fn(),
}));

// Mock the API client to prevent real HTTP calls
vi.mock("@/lib/api", () => ({
  api: {
    get: vi.fn(),
    interceptors: { request: { use: vi.fn(() => 0), eject: vi.fn() } },
  },
}));

import { useAuth } from "@clerk/nextjs";
import { api } from "@/lib/api";
import { withRole } from "@/lib/auth";

const mockUseAuth = vi.mocked(useAuth);
const mockApiGet = vi.mocked(api.get);

function makeClient() {
  return new QueryClient({ defaultOptions: { queries: { retry: false } } });
}

function Wrapper({ children }: { children: React.ReactNode }) {
  return (
    <QueryClientProvider client={makeClient()}>{children}</QueryClientProvider>
  );
}

const Dummy = () => <div>protected content</div>;

// Helper to stub window.location.href without type errors
function stubLocation() {
  Object.defineProperty(window, "location", {
    writable: true,
    value: { href: "" },
  });
}

describe("withRole", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    stubLocation();
  });

  it("renders nothing while Clerk is loading", () => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    mockUseAuth.mockReturnValue({ isLoaded: false, isSignedIn: false, getToken: vi.fn() } as any);

    const Protected = withRole(Dummy, ["admin"]);
    const { container } = render(<Protected />, { wrapper: Wrapper });
    expect(container).toBeEmptyDOMElement();
  });

  it("redirects to /sign-in when not signed in", () => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    mockUseAuth.mockReturnValue({ isLoaded: true, isSignedIn: false, getToken: vi.fn() } as any);

    const Protected = withRole(Dummy, ["admin"]);
    render(<Protected />, { wrapper: Wrapper });
    expect(window.location.href).toBe("/sign-in");
    expect(screen.queryByText("protected content")).not.toBeInTheDocument();
  });

  it("renders children when signed in with an allowed role", async () => {
    mockUseAuth.mockReturnValue({
      isLoaded: true,
      isSignedIn: true,
      getToken: vi.fn().mockResolvedValue("tok"),
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
    } as any);

    mockApiGet.mockResolvedValue({
      data: { id: "u1", role: "admin", permissions: {}, org_id: "o1", org_type: "investor" },
    });

    const Protected = withRole(Dummy, ["admin", "manager"]);
    render(<Protected />, { wrapper: Wrapper });

    await screen.findByText("protected content");
  });

  it("redirects to /dashboard when signed in with wrong role", async () => {
    mockUseAuth.mockReturnValue({
      isLoaded: true,
      isSignedIn: true,
      getToken: vi.fn().mockResolvedValue("tok"),
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
    } as any);

    mockApiGet.mockResolvedValue({
      data: { id: "u1", role: "viewer", permissions: {}, org_id: "o1", org_type: "investor" },
    });

    const Protected = withRole(Dummy, ["admin"]);
    render(<Protected />, { wrapper: Wrapper });

    await vi.waitFor(() => {
      expect(window.location.href).toBe("/dashboard");
    });
    expect(screen.queryByText("protected content")).not.toBeInTheDocument();
  });
});
