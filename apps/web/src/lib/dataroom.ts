/**
 * Data Room types and React Query hooks.
 *
 * Types mirror the FastAPI Pydantic schemas. Hooks wrap axios calls
 * with React Query for caching, optimistic updates, and pagination.
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

// ── Enums ──────────────────────────────────────────────────────────────────

export type DocumentStatus = "uploading" | "processing" | "ready" | "error";

export type DocumentClassification =
  | "financial_statement"
  | "legal_agreement"
  | "technical_study"
  | "environmental_report"
  | "permit"
  | "insurance"
  | "valuation"
  | "business_plan"
  | "presentation"
  | "correspondence"
  | "other";

export type ExtractionType =
  | "financial"
  | "kpi"
  | "clause"
  | "deadline"
  | "summary";

// ── Types ──────────────────────────────────────────────────────────────────

export interface FolderTreeNode {
  id: string;
  name: string;
  parent_folder_id: string | null;
  document_count: number;
  children: FolderTreeNode[];
}

export interface FolderResponse {
  id: string;
  name: string;
  project_id: string | null;
  parent_folder_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface DocumentResponse {
  id: string;
  name: string;
  file_type: string;
  mime_type: string;
  file_size_bytes: number;
  status: DocumentStatus;
  classification: DocumentClassification | null;
  version: number;
  parent_version_id: string | null;
  project_id: string | null;
  folder_id: string | null;
  checksum_sha256: string;
  watermark_enabled: boolean;
  metadata: Record<string, unknown> | null;
  uploaded_by: string;
  created_at: string;
  updated_at: string;
}

export interface ExtractionResponse {
  id: string;
  document_id: string;
  extraction_type: ExtractionType;
  result: Record<string, unknown>;
  model_used: string;
  confidence_score: number;
  tokens_used: number;
  processing_time_ms: number;
  created_at: string;
}

export interface DocumentDetailResponse extends DocumentResponse {
  extractions: ExtractionResponse[];
  version_count: number;
}

export interface DocumentListResponse {
  items: DocumentResponse[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface DocumentVersionResponse {
  id: string;
  name: string;
  version: number;
  file_size_bytes: number;
  status: DocumentStatus;
  checksum_sha256: string;
  uploaded_by: string;
  created_at: string;
}

export interface AccessLogEntry {
  id: string;
  user_id: string;
  action: string;
  ip_address: string | null;
  timestamp: string;
}

export interface ShareResponse {
  id: string;
  share_token: string;
  document_id: string;
  expires_at: string | null;
  watermark_enabled: boolean;
  allow_download: boolean;
  max_views: number | null;
  view_count: number;
  is_active: boolean;
  created_at: string;
}

export interface ProjectExtractionSummary {
  project_id: string;
  document_count: number;
  extraction_count: number;
  kpis: Record<string, unknown>[];
  deadlines: Record<string, unknown>[];
  financials: Record<string, unknown>[];
  classifications: Record<string, number>;
  summaries: Record<string, unknown>[];
}

export interface BulkOperationResponse {
  success_count: number;
  failure_count: number;
  errors: string[];
}

export interface PresignedUploadResponse {
  upload_url: string;
  document_id: string;
  s3_key: string;
}

// ── Query keys ─────────────────────────────────────────────────────────────

export const dataroomKeys = {
  all: ["dataroom"] as const,
  folders: (projectId: string) => [...dataroomKeys.all, "folders", projectId] as const,
  documents: (params: DocumentListParams) =>
    [...dataroomKeys.all, "documents", params] as const,
  document: (id: string) => [...dataroomKeys.all, "document", id] as const,
  versions: (id: string) => [...dataroomKeys.all, "versions", id] as const,
  accessLog: (id: string) => [...dataroomKeys.all, "access-log", id] as const,
  extractions: (id: string) => [...dataroomKeys.all, "extractions", id] as const,
  projectSummary: (projectId: string) =>
    [...dataroomKeys.all, "summary", projectId] as const,
};

// ── Params ─────────────────────────────────────────────────────────────────

export interface DocumentListParams {
  project_id?: string;
  folder_id?: string | null;
  file_type?: string;
  status?: DocumentStatus;
  search?: string;
  page?: number;
  page_size?: number;
  sort_by?: string;
  sort_order?: "asc" | "desc";
}

// ── Folder hooks ───────────────────────────────────────────────────────────

export function useFolderTree(projectId: string | undefined) {
  return useQuery({
    queryKey: dataroomKeys.folders(projectId ?? ""),
    queryFn: () =>
      api
        .get<FolderTreeNode[]>(`/dataroom/folders/${projectId}`)
        .then((r) => r.data),
    enabled: !!projectId,
  });
}

export function useCreateFolder() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: {
      name: string;
      project_id: string;
      parent_folder_id?: string | null;
    }) => api.post<FolderResponse>("/dataroom/folders", body).then((r) => r.data),
    onSuccess: (_data, vars) => {
      qc.invalidateQueries({
        queryKey: dataroomKeys.folders(vars.project_id),
      });
    },
  });
}

export function useUpdateFolder() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      folderId,
      ...body
    }: {
      folderId: string;
      name?: string;
      parent_folder_id?: string | null;
    }) =>
      api
        .put<FolderResponse>(`/dataroom/folders/${folderId}`, body)
        .then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: dataroomKeys.all });
    },
  });
}

export function useDeleteFolder() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (folderId: string) =>
      api.delete(`/dataroom/folders/${folderId}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: dataroomKeys.all });
    },
  });
}

// ── Document hooks ─────────────────────────────────────────────────────────

export function useDocuments(params: DocumentListParams) {
  return useQuery({
    queryKey: dataroomKeys.documents(params),
    queryFn: () =>
      api
        .get<DocumentListResponse>("/dataroom/documents", { params })
        .then((r) => r.data),
    enabled: !!params.project_id,
  });
}

export function useDocument(id: string | undefined) {
  return useQuery({
    queryKey: dataroomKeys.document(id ?? ""),
    queryFn: () =>
      api
        .get<DocumentDetailResponse>(`/dataroom/documents/${id}`)
        .then((r) => r.data),
    enabled: !!id,
  });
}

export function useUpdateDocument() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      documentId,
      ...body
    }: {
      documentId: string;
      name?: string;
      folder_id?: string | null;
      metadata?: Record<string, unknown>;
      watermark_enabled?: boolean;
    }) =>
      api
        .put<DocumentResponse>(`/dataroom/documents/${documentId}`, body)
        .then((r) => r.data),
    onSuccess: (_data, vars) => {
      qc.invalidateQueries({
        queryKey: dataroomKeys.document(vars.documentId),
      });
      qc.invalidateQueries({
        queryKey: [...dataroomKeys.all, "documents"],
      });
    },
  });
}

export function useDeleteDocument() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (documentId: string) =>
      api.delete(`/dataroom/documents/${documentId}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: dataroomKeys.all });
    },
  });
}

export function useDocumentDownload() {
  return useMutation({
    mutationFn: (documentId: string) =>
      api
        .get<{ download_url: string }>(
          `/dataroom/documents/${documentId}/download`
        )
        .then((r) => r.data),
  });
}

// ── Version hooks ──────────────────────────────────────────────────────────

export function useDocumentVersions(documentId: string | undefined) {
  return useQuery({
    queryKey: dataroomKeys.versions(documentId ?? ""),
    queryFn: () =>
      api
        .get<DocumentVersionResponse[]>(
          `/dataroom/documents/${documentId}/versions`
        )
        .then((r) => r.data),
    enabled: !!documentId,
  });
}

// ── Access log hooks ───────────────────────────────────────────────────────

export function useAccessLog(documentId: string | undefined) {
  return useQuery({
    queryKey: dataroomKeys.accessLog(documentId ?? ""),
    queryFn: () =>
      api
        .get<{ items: AccessLogEntry[]; total: number }>(
          `/dataroom/documents/${documentId}/access-log`
        )
        .then((r) => r.data),
    enabled: !!documentId,
  });
}

// ── Upload hooks ───────────────────────────────────────────────────────────

export function usePresignedUpload() {
  return useMutation({
    mutationFn: (body: {
      file_name: string;
      file_type: string;
      file_size_bytes: number;
      project_id: string;
      folder_id?: string | null;
      checksum_sha256: string;
    }) =>
      api
        .post<PresignedUploadResponse>("/dataroom/upload/presigned", body)
        .then((r) => r.data),
  });
}

export function useConfirmUpload() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { document_id: string }) =>
      api
        .post<{ document_id: string; status: string; message: string }>(
          "/dataroom/upload/confirm",
          body
        )
        .then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: dataroomKeys.all });
    },
  });
}

// ── Bulk hooks ─────────────────────────────────────────────────────────────

export function useBulkMove() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: {
      document_ids: string[];
      target_folder_id: string;
    }) =>
      api
        .post<BulkOperationResponse>("/dataroom/bulk/move", body)
        .then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: dataroomKeys.all });
    },
  });
}

export function useBulkDelete() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { document_ids: string[] }) =>
      api
        .post<BulkOperationResponse>("/dataroom/bulk/delete", body)
        .then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: dataroomKeys.all });
    },
  });
}

// ── Extraction hooks ───────────────────────────────────────────────────────

export function useExtractions(documentId: string | undefined) {
  return useQuery({
    queryKey: dataroomKeys.extractions(documentId ?? ""),
    queryFn: () =>
      api
        .get<{ items: ExtractionResponse[] }>(
          `/dataroom/documents/${documentId}/extractions`
        )
        .then((r) => r.data.items),
    enabled: !!documentId,
  });
}

export function useTriggerExtraction() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      documentId,
      extraction_types,
    }: {
      documentId: string;
      extraction_types?: ExtractionType[];
    }) =>
      api
        .post(`/dataroom/documents/${documentId}/extract`, {
          extraction_types,
        })
        .then((r) => r.data),
    onSuccess: (_data, vars) => {
      qc.invalidateQueries({
        queryKey: dataroomKeys.extractions(vars.documentId),
      });
    },
  });
}

export function useProjectExtractionSummary(projectId: string | undefined) {
  return useQuery({
    queryKey: dataroomKeys.projectSummary(projectId ?? ""),
    queryFn: () =>
      api
        .get<ProjectExtractionSummary>(
          `/dataroom/extractions/summary/${projectId}`
        )
        .then((r) => r.data),
    enabled: !!projectId,
  });
}

// ── Share hooks ────────────────────────────────────────────────────────────

export function useCreateShareLink() {
  return useMutation({
    mutationFn: (body: {
      document_id: string;
      expires_at?: string;
      password?: string;
      watermark_enabled?: boolean;
      allow_download?: boolean;
      max_views?: number;
    }) => api.post<ShareResponse>("/dataroom/share", body).then((r) => r.data),
  });
}

export function useRevokeShareLink() {
  return useMutation({
    mutationFn: (shareId: string) =>
      api.delete(`/dataroom/share/${shareId}`),
  });
}

// ── Helpers ────────────────────────────────────────────────────────────────

const FILE_TYPE_LABELS: Record<string, string> = {
  pdf: "PDF",
  docx: "Word",
  xlsx: "Excel",
  pptx: "PowerPoint",
  csv: "CSV",
  jpg: "Image",
  png: "Image",
};

export function fileTypeLabel(type: string): string {
  return FILE_TYPE_LABELS[type] ?? type.toUpperCase();
}

export function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  if (bytes < 1024 * 1024 * 1024)
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  return `${(bytes / (1024 * 1024 * 1024)).toFixed(1)} GB`;
}

export function classificationLabel(c: DocumentClassification): string {
  return c
    .split("_")
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");
}

export function statusColor(
  status: DocumentStatus
): "success" | "warning" | "error" | "info" {
  switch (status) {
    case "ready":
      return "success";
    case "processing":
      return "warning";
    case "uploading":
      return "info";
    case "error":
      return "error";
  }
}

/**
 * Compute SHA-256 hash of a File using the SubtleCrypto API.
 */
export async function computeSHA256(file: File): Promise<string> {
  const buffer = await file.arrayBuffer();
  const hashBuffer = await crypto.subtle.digest("SHA-256", buffer);
  const hashArray = Array.from(new Uint8Array(hashBuffer));
  return hashArray.map((b) => b.toString(16).padStart(2, "0")).join("");
}
