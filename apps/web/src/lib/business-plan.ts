/**
 * Business Planning AI — types and React Query hooks.
 */

import { useQuery, useMutation } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { BusinessPlanActionResponse, BusinessPlanResultResponse } from "@/lib/projects";

// ── Action definitions ──────────────────────────────────────────────────────

export interface BusinessPlanAction {
  icon: string;
  label: string;
  description: string;
}

export const BUSINESS_PLAN_ACTIONS = {
  executive_summary: {
    icon: "📋",
    label: "Executive Summary",
    description: "A polished 2-3 paragraph overview for investor presentations",
  },
  financial_overview: {
    icon: "💰",
    label: "Financial Projections Overview",
    description: "Narrative description of financials and return potential",
  },
  market_analysis: {
    icon: "📊",
    label: "Market & Competitive Analysis",
    description: "Market opportunity, competition, and positioning narrative",
  },
  risk_narrative: {
    icon: "⚠️",
    label: "Risk Assessment Narrative",
    description: "Structured risk summary with mitigation strategies",
  },
  esg_statement: {
    icon: "🌿",
    label: "ESG & Impact Statement",
    description: "Environmental, social, and governance impact narrative",
  },
  technical_summary: {
    icon: "⚡",
    label: "Technical Feasibility Summary",
    description: "Technical approach, capacity, and implementation narrative",
  },
  investor_pitch: {
    icon: "🎯",
    label: "Investor Pitch",
    description: "Compelling elevator pitch for investor conversations",
  },
} as const satisfies Record<string, BusinessPlanAction>;

export type BusinessPlanActionKey = keyof typeof BUSINESS_PLAN_ACTIONS;

// ── Hooks ───────────────────────────────────────────────────────────────────

export function useGenerateBusinessPlan(projectId: string) {
  return useMutation({
    mutationFn: (actionType: BusinessPlanActionKey) =>
      api
        .post<BusinessPlanActionResponse>(
          `/projects/${projectId}/ai/generate/${actionType}`
        )
        .then((r) => r.data),
  });
}

export function useBusinessPlanResult(
  projectId: string,
  taskLogId?: string
) {
  return useQuery({
    queryKey: ["business-plan", projectId, taskLogId],
    queryFn: () =>
      api
        .get<BusinessPlanResultResponse>(
          `/projects/${projectId}/ai/tasks/${taskLogId}`
        )
        .then((r) => r.data),
    enabled: !!taskLogId,
    refetchInterval: (query) => {
      const data = query.state.data;
      if (!data) return 3000;
      return data.status === "pending" || data.status === "processing"
        ? 3000
        : false;
    },
  });
}
