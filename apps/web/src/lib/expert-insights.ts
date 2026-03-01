/**
 * Expert Insights types and React Query hooks.
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

// ── Types ──────────────────────────────────────────────────────────────────

export interface Participant {
  name: string;
  role: string;
  org?: string;
}

export interface ExpertNote {
  id: string;
  org_id: string;
  project_id: string | null;
  created_by: string | null;
  note_type: string;
  title: string;
  content: string;
  ai_summary: string | null;
  key_takeaways: string[] | null;
  risk_factors_identified: string[] | null;
  linked_signal_dimensions: string[] | null;
  participants: Participant[] | null;
  meeting_date: string | null;
  enrichment_status: string;
  is_private: boolean;
  created_at: string;
  updated_at: string;
}

export interface ExpertNoteListResponse {
  items: ExpertNote[];
  total: number;
}

export interface CreateExpertNotePayload {
  project_id: string;
  note_type: string;
  title: string;
  content: string;
  participants?: Participant[];
  meeting_date?: string;
  is_private?: boolean;
}

export interface UpdateExpertNotePayload {
  title?: string;
  content?: string;
  participants?: Participant[];
  meeting_date?: string;
  is_private?: boolean;
}

export interface InsightsTimelineEntry {
  note_id: string;
  date: string | null;
  note_type: string;
  title: string;
  ai_summary: string | null;
  risk_factors: string[] | null;
  enrichment_status: string;
}

export interface InsightsTimelineResponse {
  timeline: InsightsTimelineEntry[];
  total: number;
}

// ── Query keys ─────────────────────────────────────────────────────────────

export const expertInsightsKeys = {
  all: ["expert-insights"] as const,
  lists: () => [...expertInsightsKeys.all, "list"] as const,
  list: (projectId?: string) =>
    [...expertInsightsKeys.lists(), { projectId }] as const,
  details: () => [...expertInsightsKeys.all, "detail"] as const,
  detail: (id: string) => [...expertInsightsKeys.details(), id] as const,
  timeline: (projectId: string) =>
    [...expertInsightsKeys.all, "timeline", projectId] as const,
};

// ── Hooks ──────────────────────────────────────────────────────────────────

export function useExpertNotes(projectId?: string) {
  return useQuery({
    queryKey: expertInsightsKeys.list(projectId),
    queryFn: async () => {
      const params = projectId ? { project_id: projectId } : {};
      const { data } = await api.get<ExpertNoteListResponse>(
        "/expert-insights",
        { params }
      );
      return data;
    },
  });
}

export function useExpertNote(noteId: string) {
  return useQuery({
    queryKey: expertInsightsKeys.detail(noteId),
    queryFn: async () => {
      const { data } = await api.get<ExpertNote>(
        `/expert-insights/${noteId}`
      );
      return data;
    },
    enabled: !!noteId,
  });
}

export function useInsightsTimeline(projectId: string) {
  return useQuery({
    queryKey: expertInsightsKeys.timeline(projectId),
    queryFn: async () => {
      const { data } = await api.get<InsightsTimelineResponse>(
        `/expert-insights/projects/${projectId}/timeline`
      );
      return data;
    },
    enabled: !!projectId,
  });
}

export function useCreateExpertNote(projectId?: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: CreateExpertNotePayload) => {
      const { data } = await api.post<ExpertNote>("/expert-insights", payload);
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: expertInsightsKeys.lists() });
      if (projectId) {
        qc.invalidateQueries({
          queryKey: expertInsightsKeys.timeline(projectId),
        });
      }
    },
  });
}

export function useUpdateExpertNote(noteId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: UpdateExpertNotePayload) => {
      const { data } = await api.patch<ExpertNote>(
        `/expert-insights/${noteId}`,
        payload
      );
      return data;
    },
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: expertInsightsKeys.lists() });
      qc.setQueryData(expertInsightsKeys.detail(noteId), data);
      if (data.project_id) {
        qc.invalidateQueries({
          queryKey: expertInsightsKeys.timeline(data.project_id),
        });
      }
    },
  });
}

export function useDeleteExpertNote(projectId?: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (noteId: string) => {
      await api.delete(`/expert-insights/${noteId}`);
      return noteId;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: expertInsightsKeys.lists() });
      if (projectId) {
        qc.invalidateQueries({
          queryKey: expertInsightsKeys.timeline(projectId),
        });
      }
    },
  });
}

export function useEnrichNote(projectId?: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (noteId: string) => {
      const { data } = await api.post<ExpertNote>(
        `/expert-insights/${noteId}/enrich`
      );
      return data;
    },
    onSuccess: (data) => {
      qc.setQueryData(expertInsightsKeys.detail(data.id), data);
      qc.invalidateQueries({ queryKey: expertInsightsKeys.lists() });
      if (projectId) {
        qc.invalidateQueries({
          queryKey: expertInsightsKeys.timeline(projectId),
        });
      }
    },
  });
}

// ── Note type helpers ──────────────────────────────────────────────────────

export const NOTE_TYPES = [
  { value: "call_notes", label: "Call Notes" },
  { value: "site_visit", label: "Site Visit" },
  { value: "expert_interview", label: "Expert Interview" },
  { value: "management_meeting", label: "Management Meeting" },
  { value: "reference_check", label: "Reference Check" },
] as const;

export type NoteType = (typeof NOTE_TYPES)[number]["value"];

export function getNoteTypeLabel(value: string): string {
  return NOTE_TYPES.find((t) => t.value === value)?.label ?? value;
}

export const ENRICHMENT_STATUS_LABELS: Record<string, string> = {
  pending: "Pending",
  processing: "Enriching...",
  done: "Enriched",
  failed: "Failed",
};
