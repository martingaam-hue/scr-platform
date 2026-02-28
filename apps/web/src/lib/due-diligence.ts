/**
 * Due Diligence Checklist — types and React Query hooks.
 *
 * Types mirror the FastAPI Pydantic schemas. Hooks wrap axios calls
 * with React Query for caching, optimistic updates, and state management.
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

// ── Types ────────────────────────────────────────────────────────────────────

export type DDItemStatus =
  | "pending"
  | "in_review"
  | "satisfied"
  | "partially_met"
  | "not_met"
  | "waived";

export type DDItemPriority = "required" | "recommended" | "optional";

export interface DDTemplateResponse {
  id: string;
  asset_type: string;
  deal_stage: string;
  jurisdiction_group: string | null;
  name: string;
  description: string | null;
  version: number;
  item_count: number;
}

export interface DDItemResponse {
  id: string;
  template_id: string;
  category: string;
  name: string;
  description: string | null;
  requirement_type: string;
  required_document_types: string[] | null;
  verification_criteria: string | null;
  priority: DDItemPriority;
  sort_order: number;
  estimated_time_hours: number | null;
  regulatory_reference: string | null;
}

export interface DDChecklistItemFull {
  // Item fields
  item_id: string;
  template_id: string;
  category: string;
  name: string;
  description: string | null;
  requirement_type: string;
  required_document_types: string[] | null;
  verification_criteria: string | null;
  priority: DDItemPriority;
  sort_order: number;
  estimated_time_hours: number | null;
  regulatory_reference: string | null;
  // Status fields
  status_id: string | null;
  status: DDItemStatus;
  satisfied_by_document_id: string | null;
  ai_review_result: {
    satisfied?: boolean;
    confidence?: number;
    summary?: string;
    gaps?: string[];
    recommendation?: string;
    error?: string;
  } | null;
  reviewer_notes: string | null;
  reviewed_at: string | null;
}

export interface DDChecklistResponse {
  id: string;
  project_id: string;
  org_id: string;
  template_id: string;
  investor_id: string | null;
  status: string;
  completion_percentage: number;
  total_items: number;
  completed_items: number;
  custom_items: CustomItem[];
  items_by_category: Record<string, DDChecklistItemFull[]>;
  created_at: string;
  updated_at: string;
}

export interface CustomItem {
  id: string;
  name: string;
  category: string;
  description: string | null;
  priority: DDItemPriority;
  status: DDItemStatus;
  created_at: string;
}

// ── Request types ─────────────────────────────────────────────────────────────

export interface GenerateChecklistRequest {
  project_id: string;
  investor_id?: string;
}

export interface UpdateItemStatusRequest {
  status: DDItemStatus;
  notes?: string;
  document_id?: string;
}

export interface AddCustomItemRequest {
  name: string;
  category: string;
  description?: string;
  priority?: DDItemPriority;
}

export interface TriggerAIReviewRequest {
  document_id: string;
}

// ── Query keys ────────────────────────────────────────────────────────────────

export const DD_KEYS = {
  templates: (assetType?: string) =>
    ["dd-templates", assetType].filter(Boolean) as string[],
  template: (id: string) => ["dd-template", id],
  checklists: (projectId?: string) =>
    ["dd-checklists", projectId].filter(Boolean) as string[],
  checklist: (id: string) => ["dd-checklist", id],
};

// ── Hooks ─────────────────────────────────────────────────────────────────────

/**
 * List templates, optionally filtered by asset_type.
 */
export function useTemplates(assetType?: string) {
  return useQuery({
    queryKey: DD_KEYS.templates(assetType),
    queryFn: async () => {
      const params = assetType ? `?asset_type=${assetType}` : "";
      const res = await api.get<DDTemplateResponse[]>(
        `/due-diligence/templates${params}`
      );
      return res.data;
    },
  });
}

/**
 * Get a single template with items.
 */
export function useTemplate(templateId: string | undefined) {
  return useQuery({
    queryKey: DD_KEYS.template(templateId ?? ""),
    queryFn: async () => {
      const res = await api.get(`/due-diligence/templates/${templateId}`);
      return res.data;
    },
    enabled: !!templateId,
  });
}

/**
 * List checklists for a project.
 */
export function useProjectChecklist(projectId: string | undefined) {
  return useQuery({
    queryKey: DD_KEYS.checklists(projectId),
    queryFn: async () => {
      const res = await api.get<DDChecklistResponse[]>(
        `/due-diligence/checklists?project_id=${projectId}`
      );
      // Return first checklist if it exists
      return res.data[0] ?? null;
    },
    enabled: !!projectId,
  });
}

/**
 * Get a specific checklist by ID.
 */
export function useChecklist(checklistId: string | undefined) {
  return useQuery({
    queryKey: DD_KEYS.checklist(checklistId ?? ""),
    queryFn: async () => {
      const res = await api.get<DDChecklistResponse>(
        `/due-diligence/checklists/${checklistId}`
      );
      return res.data;
    },
    enabled: !!checklistId,
  });
}

/**
 * Generate a checklist for a project.
 */
export function useGenerateChecklist() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: GenerateChecklistRequest) => {
      const res = await api.post<DDChecklistResponse>(
        "/due-diligence/checklists/generate",
        data
      );
      return res.data;
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({
        queryKey: DD_KEYS.checklists(variables.project_id),
      });
    },
  });
}

/**
 * Update the status of a checklist item.
 */
export function useUpdateItemStatus(checklistId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({
      itemId,
      ...data
    }: UpdateItemStatusRequest & { itemId: string }) => {
      const res = await api.put(
        `/due-diligence/checklists/${checklistId}/items/${itemId}/status`,
        data
      );
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: DD_KEYS.checklist(checklistId),
      });
    },
  });
}

/**
 * Add a custom item to a checklist.
 */
export function useAddCustomItem(checklistId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: AddCustomItemRequest) => {
      const res = await api.post(
        `/due-diligence/checklists/${checklistId}/items/add`,
        data
      );
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: DD_KEYS.checklist(checklistId),
      });
    },
  });
}

/**
 * Trigger AI review for a document against a checklist item.
 */
export function useTriggerAIReview(checklistId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({
      itemId,
      document_id,
    }: {
      itemId: string;
      document_id: string;
    }) => {
      const res = await api.post(
        `/due-diligence/checklists/${checklistId}/items/${itemId}/review`,
        { document_id }
      );
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: DD_KEYS.checklist(checklistId),
      });
    },
  });
}
