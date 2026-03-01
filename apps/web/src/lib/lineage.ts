/**
 * Lineage — React Query hooks for B05 data provenance feature.
 */

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";

// ── Types ──────────────────────────────────────────────────────────────────

export interface LineageRecord {
  id: string;
  field_name: string;
  source_type: string;
  source_detail: string;
  recorded_at: string;
  value_snapshot: string | null;
  actor: string | null;
}

export interface EntityLineage {
  entity_type: string;
  entity_id: string;
  fields: Record<string, LineageRecord[]>;
}

export interface FieldLineage {
  entity_type: string;
  entity_id: string;
  field_name: string;
  records: LineageRecord[];
}

export interface LineageTrace {
  entity_type: string;
  entity_id: string;
  field_name: string;
  chain: LineageRecord[];
}

// ── Query Keys ─────────────────────────────────────────────────────────────

export const lineageKeys = {
  all: ["lineage"] as const,
  entity: (entityType: string, entityId: string) =>
    [...lineageKeys.all, "entity", entityType, entityId] as const,
  field: (entityType: string, entityId: string, fieldName: string) =>
    [...lineageKeys.all, "field", entityType, entityId, fieldName] as const,
  trace: (entityType: string, entityId: string, fieldName: string) =>
    [...lineageKeys.all, "trace", entityType, entityId, fieldName] as const,
};

// ── Hooks ──────────────────────────────────────────────────────────────────

export function useEntityLineage(entityType: string, entityId: string) {
  return useQuery({
    queryKey: lineageKeys.entity(entityType, entityId),
    queryFn: () =>
      api
        .get<EntityLineage>(`/lineage/${entityType}/${entityId}`)
        .then((r) => r.data),
    enabled: !!entityId,
  });
}

export function useFieldLineage(
  entityType: string,
  entityId: string,
  fieldName: string
) {
  return useQuery({
    queryKey: lineageKeys.field(entityType, entityId, fieldName),
    queryFn: () =>
      api
        .get<FieldLineage>(`/lineage/${entityType}/${entityId}/${fieldName}`)
        .then((r) => r.data),
    enabled: !!entityId && !!fieldName,
  });
}

export function useLineageTrace(
  entityType: string,
  entityId: string,
  fieldName: string
) {
  return useQuery({
    queryKey: lineageKeys.trace(entityType, entityId, fieldName),
    queryFn: () =>
      api
        .get<LineageTrace>(
          `/lineage/trace/${entityType}/${entityId}/${fieldName}`
        )
        .then((r) => r.data),
    enabled: !!entityId && !!fieldName,
  });
}
