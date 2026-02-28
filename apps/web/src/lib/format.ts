/**
 * Shared formatting utilities for the SCR Platform frontend.
 */

/**
 * Format a number as a EUR currency string.
 * e.g. 1_500_000 → "€1.5M"
 */
export function formatCurrency(value: number, currency = "EUR"): string {
  if (value >= 1_000_000_000) return `€${(value / 1_000_000_000).toFixed(1)}B`
  if (value >= 1_000_000) return `€${(value / 1_000_000).toFixed(1)}M`
  if (value >= 1_000) return `€${(value / 1_000).toFixed(0)}k`
  return `€${value.toFixed(0)}`
}

/**
 * Format a decimal as a percentage string.
 * e.g. 0.153 → "15.3%" OR 15.3 → "15.3%" (accepts both forms)
 */
export function formatPct(value: number, decimals = 1): string {
  const pct = value < 1 && value > -1 ? value * 100 : value
  return `${pct.toFixed(decimals)}%`
}

/**
 * Format an ISO date string as a human-readable date.
 * e.g. "2025-03-15T10:00:00Z" → "15 Mar 2025"
 */
export function formatDate(isoString: string | null | undefined): string {
  if (!isoString) return "—"
  try {
    return new Date(isoString).toLocaleDateString("en-GB", {
      day: "numeric",
      month: "short",
      year: "numeric",
    })
  } catch {
    return isoString
  }
}

/**
 * Format a number as a multiplier.
 * e.g. 1.85 → "1.85x"
 */
export function formatMultiple(value: number, decimals = 2): string {
  return `${value.toFixed(decimals)}x`
}
