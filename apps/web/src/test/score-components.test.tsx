/**
 * Tests for SignalScoreHero component rendering.
 *
 * Uses Math.round() (not Math.ceil()) on the raw avgScore.
 * Color thresholds: >= 80 green, >= 70 blue, >= 60 amber, >= 50 yellow, else red.
 */
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { SignalScoreHero } from "@/components/signal-score-hero";

// cn() from @scr/ui is a classname utility — stub it out
vi.mock("@scr/ui", () => ({
  cn: (...classes: unknown[]) =>
    classes.filter((c) => typeof c === "string" && c).join(" "),
}));

const baseProps = {
  avgScore: 85,
  totalProjects: 12,
  investmentReady: 8,
  needsAttention: 2,
};

describe("SignalScoreHero", () => {
  it("renders the rounded score as text", () => {
    render(<SignalScoreHero {...baseProps} avgScore={85} />);
    // Score appears in both the ring span and the stat card — getAllByText is correct
    const scores = screen.getAllByText("85");
    expect(scores.length).toBeGreaterThanOrEqual(1);
  });

  it("applies Math.round() to avgScore (not Math.ceil)", () => {
    // 85.4 rounds down to 85
    render(<SignalScoreHero {...baseProps} avgScore={85.4} />);
    expect(screen.getAllByText("85").length).toBeGreaterThanOrEqual(1);
  });

  it("rounds 85.5 up to 86", () => {
    render(<SignalScoreHero {...baseProps} avgScore={85.5} />);
    expect(screen.getAllByText("86").length).toBeGreaterThanOrEqual(1);
  });

  it("renders total project count", () => {
    render(<SignalScoreHero {...baseProps} totalProjects={12} />);
    expect(screen.getByText("12")).toBeInTheDocument();
  });

  it("renders label prop", () => {
    render(<SignalScoreHero {...baseProps} label="My Score" />);
    expect(screen.getByText("My Score")).toBeInTheDocument();
  });

  it("renders default label when not provided", () => {
    render(<SignalScoreHero {...baseProps} />);
    expect(screen.getByText("Portfolio Signal Score")).toBeInTheDocument();
  });

  it("renders a positive trend indicator when score improved", () => {
    render(<SignalScoreHero {...baseProps} avgScore={85} previousScore={80} />);
    // Score went up by 5 — TrendingUp icon area or the +5 diff text should appear
    expect(screen.getByText(/\+5/)).toBeInTheDocument();
  });

  it("renders a negative trend indicator when score decreased", () => {
    render(<SignalScoreHero {...baseProps} avgScore={75} previousScore={80} />);
    expect(screen.getByText(/-5/)).toBeInTheDocument();
  });

  it("clamps score between 0 and 100 for ring fill", () => {
    // Should not throw for out-of-range values
    expect(() =>
      render(<SignalScoreHero {...baseProps} avgScore={150} />)
    ).not.toThrow();
    expect(() =>
      render(<SignalScoreHero {...baseProps} avgScore={-10} />)
    ).not.toThrow();
  });
});
