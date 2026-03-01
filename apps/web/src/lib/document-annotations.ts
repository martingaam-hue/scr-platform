/**
 * Document Annotations — React Query hooks.
 *
 * Mirrors the FastAPI /annotations endpoints.
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

// ── Types ─────────────────────────────────────────────────────────────────

export interface AnnotationPosition {
  x: number;
  y: number;
  width: number;
  height: number;
  rects?: Array<{ x: number; y: number; w: number; h: number }>;
}

export interface Annotation {
  id: string;
  document_id: string;
  annotation_type: "highlight" | "note" | "bookmark" | "question_link";
  page_number: number;
  position: AnnotationPosition;
  content: string | null;
  color: string;
  linked_qa_question_id: string | null;
  linked_citation_id: string | null;
  is_private: boolean;
  created_by: string | null;
  created_at: string;
  updated_at: string;
}

export interface CreateAnnotationPayload {
  document_id: string;
  annotation_type: Annotation["annotation_type"];
  page_number: number;
  position: AnnotationPosition;
  content?: string | null;
  color?: string;
  linked_qa_question_id?: string | null;
  linked_citation_id?: string | null;
  is_private?: boolean;
}

export interface UpdateAnnotationPayload {
  annotationId: string;
  content?: string | null;
  color?: string | null;
  is_private?: boolean | null;
}

// ── Query keys ────────────────────────────────────────────────────────────

export const annotationKeys = {
  all: ["annotations"] as const,
  byDocument: (documentId: string) =>
    [...annotationKeys.all, "document", documentId] as const,
};

// ── Hooks ─────────────────────────────────────────────────────────────────

export function useAnnotations(documentId: string | undefined) {
  return useQuery<Annotation[]>({
    queryKey: annotationKeys.byDocument(documentId ?? ""),
    queryFn: async () => {
      const { data } = await api.get<Annotation[]>("/annotations", {
        params: { document_id: documentId },
      });
      return data;
    },
    enabled: !!documentId,
  });
}

export function useCreateAnnotation() {
  const qc = useQueryClient();
  return useMutation<Annotation, Error, CreateAnnotationPayload>({
    mutationFn: async (payload) => {
      const { data } = await api.post<Annotation>("/annotations", payload);
      return data;
    },
    onSuccess: (_data, vars) => {
      qc.invalidateQueries({
        queryKey: annotationKeys.byDocument(vars.document_id),
      });
    },
  });
}

export function useUpdateAnnotation() {
  const qc = useQueryClient();
  return useMutation<Annotation, Error, UpdateAnnotationPayload & { document_id: string }>({
    mutationFn: async ({ annotationId, document_id: _docId, ...body }) => {
      const { data } = await api.patch<Annotation>(
        `/annotations/${annotationId}`,
        body
      );
      return data;
    },
    onSuccess: (_data, vars) => {
      qc.invalidateQueries({
        queryKey: annotationKeys.byDocument(vars.document_id),
      });
    },
  });
}

export function useDeleteAnnotation() {
  const qc = useQueryClient();
  return useMutation<void, Error, { annotationId: string; document_id: string }>({
    mutationFn: async ({ annotationId }) => {
      await api.delete(`/annotations/${annotationId}`);
    },
    onSuccess: (_data, vars) => {
      qc.invalidateQueries({
        queryKey: annotationKeys.byDocument(vars.document_id),
      });
    },
  });
}
