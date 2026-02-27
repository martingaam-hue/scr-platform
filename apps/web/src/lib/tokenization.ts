/**
 * Tokenization types and React Query hooks.
 */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api";

// ── Types ───────────────────────────────────────────────────────────────────

export interface TokenHolding {
  holder_name: string;
  holder_type: string; // founder, investor, advisor, treasury
  tokens: number;
  percentage: number;
  locked_until: string | null;
}

export interface TokenizationRecord {
  id: string;
  project_id: string;
  token_name: string;
  token_symbol: string;
  total_supply: number;
  token_price_usd: number;
  market_cap_usd: number;
  blockchain: string;
  token_type: string;
  regulatory_framework: string;
  minimum_investment_usd: number;
  lock_up_period_days: number;
  status: string; // draft, pending_review, active, paused
  cap_table: TokenHolding[];
  transfer_history: Array<Record<string, unknown>>;
  created_at: string;
  updated_at: string;
}

export interface TokenizationRequest {
  project_id: string;
  token_name: string;
  token_symbol: string;
  total_supply: number;
  token_price_usd: number;
  blockchain?: string;
  token_type?: string;
  regulatory_framework?: string;
  minimum_investment_usd?: number;
  lock_up_period_days?: number;
  metadata?: Record<string, unknown>;
}

export interface TransferRequest {
  from_holder: string;
  to_holder: string;
  tokens: number;
  price_per_token_usd?: number;
  notes?: string;
}

// ── Query key factory ────────────────────────────────────────────────────────

export const tokenizationKeys = {
  all: ["tokenization"] as const,
  lists: () => [...tokenizationKeys.all, "list"] as const,
  project: (id: string) => [...tokenizationKeys.all, id] as const,
};

// ── Hooks ────────────────────────────────────────────────────────────────────

export function useTokenizations() {
  return useQuery({
    queryKey: tokenizationKeys.lists(),
    queryFn: () =>
      api.get<TokenizationRecord[]>("/tokenization").then((r) => r.data),
  });
}

export function useTokenization(projectId?: string) {
  return useQuery({
    queryKey: tokenizationKeys.project(projectId ?? ""),
    queryFn: () =>
      api
        .get<TokenizationRecord>(`/tokenization/${projectId}`)
        .then((r) => r.data),
    enabled: !!projectId,
  });
}

export function useCreateTokenization() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (req: TokenizationRequest) =>
      api
        .post<TokenizationRecord>("/tokenization", req)
        .then((r) => r.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: tokenizationKeys.lists() });
    },
  });
}

export function useAddTransfer(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (req: TransferRequest) =>
      api
        .post<TokenizationRecord>(`/tokenization/${projectId}/transfer`, req)
        .then((r) => r.data),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: tokenizationKeys.project(projectId),
      });
      queryClient.invalidateQueries({ queryKey: tokenizationKeys.lists() });
    },
  });
}

// ── Helpers ──────────────────────────────────────────────────────────────────

export function statusBadgeVariant(
  status: string,
): "success" | "warning" | "error" | "neutral" {
  switch (status) {
    case "active":
      return "success";
    case "pending_review":
      return "warning";
    case "paused":
      return "neutral";
    default:
      return "neutral";
  }
}

export function blockchainColor(blockchain: string): string {
  switch (blockchain.toLowerCase()) {
    case "ethereum":
      return "text-indigo-600";
    case "polygon":
      return "text-purple-600";
    case "solana":
      return "text-green-600";
    default:
      return "text-neutral-600";
  }
}
