/**
 * Tests for risk score display utilities.
 *
 * IMPORTANT: The risk score scale is INVERTED — lower score = less risk = better.
 * 0-20   → green  (Low Risk / Well Managed)
 * 21-40  → blue   (Acceptable)
 * 41-60  → amber  (Needs Attention)
 * 61-80  → yellow (High Risk)
 * 81-100 → red    (Critical)
 */
import { describe, expect, it } from "vitest";

import { riskScoreColor } from "@/lib/alley-risk";
import { domainRiskColor, domainRiskLabel } from "@/lib/risk";

describe("riskScoreColor — lower is better (hex colors)", () => {
  it("score <= 20 → green (low risk / well managed)", () => {
    expect(riskScoreColor(0)).toBe("#22c55e");
    expect(riskScoreColor(10)).toBe("#22c55e");
    expect(riskScoreColor(20)).toBe("#22c55e");
  });

  it("score 21-40 → blue (acceptable)", () => {
    expect(riskScoreColor(21)).toBe("#3b82f6");
    expect(riskScoreColor(30)).toBe("#3b82f6");
    expect(riskScoreColor(40)).toBe("#3b82f6");
  });

  it("score 41-60 → amber (needs attention)", () => {
    expect(riskScoreColor(41)).toBe("#f59e0b");
    expect(riskScoreColor(55)).toBe("#f59e0b");
    expect(riskScoreColor(60)).toBe("#f59e0b");
  });

  it("score 61-80 → yellow (high risk)", () => {
    expect(riskScoreColor(61)).toBe("#eab308");
    expect(riskScoreColor(75)).toBe("#eab308");
    expect(riskScoreColor(80)).toBe("#eab308");
  });

  it("score > 80 → red (critical)", () => {
    expect(riskScoreColor(81)).toBe("#ef4444");
    expect(riskScoreColor(90)).toBe("#ef4444");
    expect(riskScoreColor(100)).toBe("#ef4444");
  });
});

describe("domainRiskLabel", () => {
  it("null → Unknown", () => {
    expect(domainRiskLabel(null)).toBe("Unknown");
  });

  it("score <= 20 → Low Risk", () => {
    expect(domainRiskLabel(0)).toBe("Low Risk");
    expect(domainRiskLabel(10)).toBe("Low Risk");
    expect(domainRiskLabel(20)).toBe("Low Risk");
  });

  it("score <= 40 → Acceptable", () => {
    expect(domainRiskLabel(30)).toBe("Acceptable");
    expect(domainRiskLabel(40)).toBe("Acceptable");
  });

  it("score <= 60 → Needs Attention", () => {
    expect(domainRiskLabel(55)).toBe("Needs Attention");
    expect(domainRiskLabel(60)).toBe("Needs Attention");
  });

  it("score <= 80 → High Risk", () => {
    expect(domainRiskLabel(70)).toBe("High Risk");
    expect(domainRiskLabel(80)).toBe("High Risk");
  });

  it("score > 80 → Critical", () => {
    expect(domainRiskLabel(90)).toBe("Critical");
    expect(domainRiskLabel(100)).toBe("Critical");
  });
});

describe("domainRiskColor — CSS class version (lower is better)", () => {
  it("null → neutral", () => {
    expect(domainRiskColor(null)).toBe("text-neutral-400");
  });

  it("score <= 20 → green", () => {
    expect(domainRiskColor(10)).toBe("text-green-600");
  });

  it("score <= 40 → blue", () => {
    expect(domainRiskColor(30)).toBe("text-blue-600");
  });

  it("score <= 60 → amber", () => {
    expect(domainRiskColor(55)).toBe("text-amber-500");
  });

  it("score <= 80 → yellow", () => {
    expect(domainRiskColor(75)).toBe("text-yellow-600");
  });

  it("score > 80 → red", () => {
    expect(domainRiskColor(90)).toBe("text-red-600");
  });
});
