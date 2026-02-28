/**
 * Blockchain Audit Trail — types and React Query hooks.
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

// ── Types ───────────────────────────────────────────────────────────────────

export interface AnchorResponse {
  id: string;
  event_type: string;
  entity_type: string;
  entity_id: string;
  data_hash: string;
  merkle_root: string | null;
  chain: string;
  tx_hash: string | null;
  block_number: number | null;
  status: "pending" | "anchored" | "failed";
  anchored_at: string | null;
}

export interface AuditReport {
  total: number;
  anchored: number;
  pending: number;
  items: AnchorResponse[];
}

export interface VerifyResult {
  verified: boolean;
  entity_type: string;
  entity_id: string;
  anchor?: AnchorResponse;
  message?: string;
}

// ── Query Keys ──────────────────────────────────────────────────────────────

export const blockchainKeys = {
  all: ["blockchain"] as const,
  report: () => [...blockchainKeys.all, "report"] as const,
  entity: (entityType: string, entityId: string) =>
    [...blockchainKeys.all, "entity", entityType, entityId] as const,
  verify: (entityType: string, entityId: string) =>
    [...blockchainKeys.all, "verify", entityType, entityId] as const,
};

// ── Hooks ───────────────────────────────────────────────────────────────────

export function useAuditReport() {
  return useQuery({
    queryKey: blockchainKeys.report(),
    queryFn: () =>
      api.get<AuditReport>("/blockchain-audit/audit-report").then((r) => r.data),
    refetchInterval: 30_000, // refresh every 30s
  });
}

export function useEntityAnchors(
  entityType: string,
  entityId: string | undefined
) {
  return useQuery({
    queryKey: blockchainKeys.entity(entityType, entityId ?? ""),
    queryFn: () =>
      api
        .get<AnchorResponse[]>(
          `/blockchain-audit/anchors/${entityType}/${entityId}`
        )
        .then((r) => r.data),
    enabled: !!entityId,
  });
}

export function useVerifyAnchor(
  entityType: string,
  entityId: string | undefined
) {
  return useQuery({
    queryKey: blockchainKeys.verify(entityType, entityId ?? ""),
    queryFn: () =>
      api
        .get<VerifyResult>(
          `/blockchain-audit/verify/${entityType}/${entityId}`
        )
        .then((r) => r.data),
    enabled: !!entityId,
  });
}

export function useBatchSubmit() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () =>
      api.post("/blockchain-audit/batch-submit").then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: blockchainKeys.all });
    },
  });
}
