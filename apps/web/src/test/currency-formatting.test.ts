/**
 * Tests for financial display utilities in lib/format.ts.
 *
 * formatCurrency: uses $ (not €), abbreviates M/B/k
 * formatPct: accepts both decimal (0.142) and percentage (14.2) forms
 * formatMultiple: appends "x"
 * formatDate: ISO → human-readable (locale-dependent, tested loosely)
 */
import { describe, expect, it } from "vitest";

import { formatCurrency, formatDate, formatMultiple, formatPct } from "@/lib/format";

describe("formatCurrency", () => {
  it("formats billions with 1 decimal", () => {
    expect(formatCurrency(1_200_000_000)).toBe("$1.2B");
    expect(formatCurrency(2_500_000_000)).toBe("$2.5B");
  });

  it("formats millions with 1 decimal", () => {
    expect(formatCurrency(1_234_567)).toBe("$1.2M");
    expect(formatCurrency(10_000_000)).toBe("$10.0M");
  });

  it("formats thousands with 0 decimals", () => {
    expect(formatCurrency(5_000)).toBe("$5k");
    expect(formatCurrency(1_500)).toBe("$2k"); // 1.5 rounds to 2
  });

  it("formats sub-thousand with 0 decimals", () => {
    expect(formatCurrency(500)).toBe("$500");
    expect(formatCurrency(0)).toBe("$0");
  });

  it("uses $ currency symbol (not €)", () => {
    expect(formatCurrency(1_000_000)).toMatch(/^\$/);
  });
});

describe("formatPct", () => {
  it("converts decimal form < 1 to percentage", () => {
    expect(formatPct(0.1423)).toBe("14.2%");
    expect(formatPct(0.05)).toBe("5.0%");
    expect(formatPct(0.999)).toBe("99.9%");
  });

  it("treats values >= 1 as already a percentage", () => {
    expect(formatPct(14.23)).toBe("14.2%");
    expect(formatPct(100)).toBe("100.0%");
  });

  it("handles zero", () => {
    expect(formatPct(0)).toBe("0.0%");
  });

  it("handles negative decimals", () => {
    expect(formatPct(-0.05)).toBe("-5.0%");
  });

  it("respects custom decimal places", () => {
    expect(formatPct(0.1423, 2)).toBe("14.23%");
    expect(formatPct(0.1423, 0)).toBe("14%");
  });
});

describe("formatMultiple", () => {
  it("appends x suffix", () => {
    expect(formatMultiple(1.34)).toBe("1.34x");
    expect(formatMultiple(2.0)).toBe("2.00x");
    expect(formatMultiple(1.0)).toBe("1.00x");
  });

  it("respects custom decimal places", () => {
    expect(formatMultiple(1.5, 1)).toBe("1.5x");
    expect(formatMultiple(2.555, 0)).toBe("3x");
  });
});

describe("formatDate", () => {
  it("returns em-dash for null/undefined/empty", () => {
    expect(formatDate(null)).toBe("—");
    expect(formatDate(undefined)).toBe("—");
    expect(formatDate("")).toBe("—");
  });

  it("formats ISO string to human-readable date", () => {
    const result = formatDate("2025-03-15T10:00:00Z");
    // Locale-dependent but should contain 2025 and Mar
    expect(result).toContain("2025");
    expect(result).toMatch(/Mar/i);
  });
});
