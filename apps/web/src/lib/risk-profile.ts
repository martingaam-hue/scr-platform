/**
 * Investor Risk Profile — React Query hooks.
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

// ── Types ──────────────────────────────────────────────────────────────────

export interface AssessmentRequest {
  experience_level: "none" | "limited" | "moderate" | "extensive";
  investment_horizon_years: number;
  loss_tolerance_percentage: number;
  liquidity_needs: "high" | "moderate" | "low";
  concentration_max_percentage: number;
  max_drawdown_tolerance: number;
}

export interface RiskProfileResponse {
  has_profile: boolean;
  risk_category: string | null;
  sophistication_score: number | null;
  risk_appetite_score: number | null;
  recommended_allocation: Record<string, number> | null;
  experience_level: string | null;
  investment_horizon_years: number | null;
  loss_tolerance_percentage: number | null;
  liquidity_needs: string | null;
  concentration_max_percentage: number | null;
  max_drawdown_tolerance: number | null;
}

// ── Query key factories ─────────────────────────────────────────────────────

export const riskProfileKeys = {
  profile: ["risk-profile"] as const,
};

// ── Hooks ───────────────────────────────────────────────────────────────────

export function useRiskProfile() {
  return useQuery({
    queryKey: riskProfileKeys.profile,
    queryFn: async () => {
      const { data } = await api.get<RiskProfileResponse>("/risk-profile");
      return data;
    },
  });
}

export function useSubmitRiskAssessment() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: AssessmentRequest) => {
      const { data } = await api.post<RiskProfileResponse>("/risk-profile/assess", body);
      return data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: riskProfileKeys.profile }),
  });
}

// ── Formatting helpers ──────────────────────────────────────────────────────

export const RISK_CATEGORY_LABELS: Record<string, string> = {
  conservative: "Conservative",
  moderate: "Moderate",
  balanced: "Balanced",
  growth: "Growth",
  aggressive: "Aggressive",
};

export const RISK_CATEGORY_COLORS: Record<string, string> = {
  conservative: "#22c55e",
  moderate: "#84cc16",
  balanced: "#eab308",
  growth: "#f97316",
  aggressive: "#ef4444",
};

export const EXPERIENCE_LABELS: Record<string, string> = {
  none: "No experience",
  limited: "Limited (< 2 years)",
  moderate: "Moderate (2–5 years)",
  extensive: "Extensive (5+ years)",
};

export const LIQUIDITY_LABELS: Record<string, string> = {
  high: "High — need access within 1 year",
  moderate: "Moderate — 1–3 year horizon",
  low: "Low — long-term lock-up acceptable",
};
