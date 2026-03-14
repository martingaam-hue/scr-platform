/**
 * Tests for Signal Score color/style helpers in lib/signal-score.ts.
 *
 * The exported functions return Tailwind CSS class strings, not hex colors.
 * Thresholds: >= 80 green, >= 60 amber, < 60 red.
 */
import { describe, expect, it } from "vitest";

import {
  priorityColor,
  scoreBgColor,
  scoreColor,
} from "@/lib/signal-score";

describe("scoreColor", () => {
  it("returns green for score >= 80", () => {
    expect(scoreColor(80)).toBe("text-green-600");
    expect(scoreColor(85)).toBe("text-green-600");
    expect(scoreColor(95)).toBe("text-green-600");
    expect(scoreColor(100)).toBe("text-green-600");
  });

  it("returns amber for 60 <= score < 80", () => {
    expect(scoreColor(60)).toBe("text-amber-600");
    expect(scoreColor(65)).toBe("text-amber-600");
    expect(scoreColor(75)).toBe("text-amber-600");
    expect(scoreColor(79)).toBe("text-amber-600");
  });

  it("returns red for score < 60", () => {
    expect(scoreColor(0)).toBe("text-red-600");
    expect(scoreColor(45)).toBe("text-red-600");
    expect(scoreColor(55)).toBe("text-red-600");
    expect(scoreColor(59)).toBe("text-red-600");
  });

  it("boundary at 80 is inclusive-green", () => {
    expect(scoreColor(79)).toBe("text-amber-600");
    expect(scoreColor(80)).toBe("text-green-600");
  });

  it("boundary at 60 is inclusive-amber", () => {
    expect(scoreColor(59)).toBe("text-red-600");
    expect(scoreColor(60)).toBe("text-amber-600");
  });
});

describe("scoreBgColor", () => {
  it("returns green bg for score >= 80", () => {
    expect(scoreBgColor(80)).toBe("bg-green-50");
    expect(scoreBgColor(90)).toBe("bg-green-50");
    expect(scoreBgColor(100)).toBe("bg-green-50");
  });

  it("returns amber bg for 60-79", () => {
    expect(scoreBgColor(60)).toBe("bg-amber-50");
    expect(scoreBgColor(65)).toBe("bg-amber-50");
    expect(scoreBgColor(79)).toBe("bg-amber-50");
  });

  it("returns red bg for score < 60", () => {
    expect(scoreBgColor(0)).toBe("bg-red-50");
    expect(scoreBgColor(40)).toBe("bg-red-50");
    expect(scoreBgColor(59)).toBe("bg-red-50");
  });
});

describe("priorityColor", () => {
  it("maps high → error", () => {
    expect(priorityColor("high")).toBe("error");
  });

  it("maps medium → warning", () => {
    expect(priorityColor("medium")).toBe("warning");
  });

  it("maps low and unknown values → neutral", () => {
    expect(priorityColor("low")).toBe("neutral");
    expect(priorityColor("unknown")).toBe("neutral");
    expect(priorityColor("")).toBe("neutral");
  });
});
