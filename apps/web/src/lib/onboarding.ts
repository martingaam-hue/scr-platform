/**
 * Onboarding types and React Query hooks.
 */

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import type { SCRUser } from "@/lib/auth";

// ── Types ──────────────────────────────────────────────────────────────

export interface OnboardingData {
  org_type: "investor" | "ally";
  org_name: string;
  org_industry?: string;
  org_geography?: string;
  org_size?: string;
  org_aum?: string;
  preferences: Record<string, unknown>;
  first_action?: {
    name: string;
    project_type: string;
    geography_country?: string;
    total_investment_required?: string;
    description?: string;
    currency?: string;
  } | null;
}

export interface OnboardingResponse {
  success: boolean;
  org_type: string;
  created_entities: Record<string, unknown>;
  redirect_to: string;
}

// ── Hooks ──────────────────────────────────────────────────────────────

export function useCompleteOnboarding() {
  const qc = useQueryClient();
  const router = useRouter();

  return useMutation({
    mutationFn: (data: OnboardingData) =>
      api.put<OnboardingResponse>("/onboarding/complete", data).then((r) => r.data),
    onSuccess: (result) => {
      // Refresh the user profile so dashboard picks up new org_type + preferences
      qc.invalidateQueries({ queryKey: ["auth", "me"] });
      router.replace(result.redirect_to);
    },
  });
}

// ── Helpers ─────────────────────────────────────────────────────────────

export function isOnboardingComplete(user: SCRUser | null): boolean {
  if (!user) return false;
  return user.preferences?.onboarding_completed === true;
}
