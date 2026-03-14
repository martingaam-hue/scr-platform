/**
 * Tests for React Query hooks in lib/signal-score.ts and lib/projects.ts.
 *
 * The API is mocked — no real HTTP calls. Tests verify:
 * - Hooks return loading state initially
 * - Hooks return data when the API resolves
 * - Error state is surfaced correctly
 * - Query key factories produce stable, predictable keys
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import React from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/api", () => ({
  api: { get: vi.fn() },
}));

// signal-score.ts imports mock-data at module level; stub it out
vi.mock("@/lib/mock-data", () => ({
  MOCK_SIGNAL_DETAILS: null,
  MOCK_SIGNAL_GAPS: null,
  MOCK_SIGNAL_HISTORY: [],
  MOCK_PROJECTS: [],
}));

import { api } from "@/lib/api";
import { signalScoreKeys, useSignalScore } from "@/lib/signal-score";
import { projectKeys } from "@/lib/projects";

const mockGet = vi.mocked(api.get);

function makeWrapper() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return ({ children }: { children: React.ReactNode }) =>
    React.createElement(QueryClientProvider, { client }, children);
}

const PROJECT_ID = "proj-123";

// ── Query key factories ─────────────────────────────────────────────────────

describe("signalScoreKeys", () => {
  it("all() produces a stable base key", () => {
    expect(signalScoreKeys.all).toEqual(["signal-score"]);
  });

  it("latest(id) includes the project id", () => {
    const key = signalScoreKeys.latest(PROJECT_ID);
    expect(key).toContain(PROJECT_ID);
  });

  it("details(id) includes the project id", () => {
    const key = signalScoreKeys.details(PROJECT_ID);
    expect(key).toContain(PROJECT_ID);
  });
});

describe("projectKeys", () => {
  it("all() produces a stable base key", () => {
    expect(projectKeys.all).toEqual(["projects"]);
  });

  it("detail(id) includes the project id", () => {
    const key = projectKeys.detail(PROJECT_ID);
    expect(key).toContain(PROJECT_ID);
  });
});

// ── useSignalScore ───────────────────────────────────────────────────────────

const MOCK_SCORE = {
  id: "score-1",
  project_id: PROJECT_ID,
  overall_score: 82,
  dimensions: [],
  status: "completed",
};

describe("useSignalScore", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("starts in loading state", () => {
    mockGet.mockReturnValue(new Promise(() => {})); // never resolves
    const { result } = renderHook(
      () => useSignalScore(PROJECT_ID),
      { wrapper: makeWrapper() }
    );
    expect(result.current.isLoading).toBe(true);
    expect(result.current.data).toBeUndefined();
  });

  it("returns data after API resolves", async () => {
    mockGet.mockResolvedValueOnce({ data: MOCK_SCORE });
    const { result } = renderHook(
      () => useSignalScore(PROJECT_ID),
      { wrapper: makeWrapper() }
    );

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toEqual(MOCK_SCORE);
    expect(result.current.data?.overall_score).toBe(82);
  });

  it("surfaces error state when API fails", async () => {
    mockGet.mockRejectedValueOnce(new Error("Network error"));
    const { result } = renderHook(
      () => useSignalScore(PROJECT_ID),
      { wrapper: makeWrapper() }
    );

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(result.current.error).toBeInstanceOf(Error);
    expect(result.current.data).toBeUndefined();
  });

  it("does not fetch when projectId is undefined", () => {
    mockGet.mockReturnValue(new Promise(() => {}));
    const { result } = renderHook(
      () => useSignalScore(undefined),
      { wrapper: makeWrapper() }
    );
    // fetchStatus 'idle' means the query is disabled
    expect(result.current.fetchStatus).toBe("idle");
    expect(mockGet).not.toHaveBeenCalled();
  });
});
