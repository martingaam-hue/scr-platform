/**
 * AI Document Redaction — types and React Query hooks.
 *
 * Mirrors the FastAPI Pydantic schemas defined in
 * apps/api/app/modules/redaction/schemas.py
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

// ── Types ───────────────────────────────────────────────────────────────────

export type RedactionStatus =
  | "pending"
  | "analyzing"
  | "review"
  | "applying"
  | "done"
  | "failed";

export interface DetectedEntity {
  id: number;
  entity_type: string;
  text: string;
  page: number;
  confidence: number;
  position: { x: number; y: number; width: number; height: number };
  is_high_sensitivity: boolean;
}

export interface RedactionJob {
  id: string;
  document_id: string;
  status: RedactionStatus;
  detected_entities: DetectedEntity[] | null;
  approved_redactions: DetectedEntity[] | null;
  entity_count: number;
  approved_count: number;
  redacted_document_id: string | null;
  redacted_s3_key: string | null;
  error_message: string | null;
  created_at: string;
  updated_at: string;
}

export interface EntityTypeInfo {
  entity_type: string;
  is_high_sensitivity: boolean;
}

export interface RedactionRules {
  entity_types: EntityTypeInfo[];
  high_sensitivity_types: string[];
}

export interface AnalyzeDocumentRequest {
  document_text?: string;
}

export interface ApproveRedactionsRequest {
  approved_entity_ids: number[];
}

// ── Query keys ───────────────────────────────────────────────────────────────

const KEYS = {
  jobs: (documentId?: string) =>
    documentId
      ? (["redaction", "jobs", documentId] as const)
      : (["redaction", "jobs"] as const),
  job: (jobId: string) => ["redaction", "job", jobId] as const,
  rules: () => ["redaction", "rules"] as const,
};

// ── Hooks ────────────────────────────────────────────────────────────────────

/** List redaction jobs, optionally scoped to a single document. */
export function useRedactionJobs(documentId?: string) {
  return useQuery<RedactionJob[]>({
    queryKey: KEYS.jobs(documentId),
    queryFn: async () => {
      const params = documentId ? { document_id: documentId } : {};
      const { data } = await api.get("/redaction/jobs", { params });
      return data;
    },
  });
}

/** Fetch a single redaction job by ID, polling while it is in-progress. */
export function useRedactionJob(jobId: string, enabled = true) {
  return useQuery<RedactionJob>({
    queryKey: KEYS.job(jobId),
    queryFn: async () => {
      const { data } = await api.get(`/redaction/jobs/${jobId}`);
      return data;
    },
    enabled: enabled && !!jobId,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      // Poll while the job is still running
      if (status === "pending" || status === "analyzing" || status === "applying") {
        return 2000; // 2 s
      }
      return false;
    },
  });
}

/** Return the list of entity types and which are high-sensitivity. */
export function useRedactionRules() {
  return useQuery<RedactionRules>({
    queryKey: KEYS.rules(),
    queryFn: async () => {
      const { data } = await api.get("/redaction/rules");
      return data;
    },
    staleTime: Infinity, // static data
  });
}

/** Create a redaction job and queue PII analysis. Returns { job_id, status }. */
export function useAnalyzeDocument() {
  const qc = useQueryClient();
  return useMutation<
    { job_id: string; status: string },
    Error,
    { document_id: string; document_text?: string }
  >({
    mutationFn: async ({ document_id, document_text }) => {
      const { data } = await api.post(
        `/redaction/analyze/${document_id}`,
        document_text ? { document_text } : {}
      );
      return data;
    },
    onSuccess: (_data, variables) => {
      qc.invalidateQueries({ queryKey: KEYS.jobs(variables.document_id) });
      qc.invalidateQueries({ queryKey: KEYS.jobs() });
    },
  });
}

/** Approve a subset of detected entities for actual redaction. */
export function useApproveRedactions() {
  const qc = useQueryClient();
  return useMutation<
    RedactionJob,
    Error,
    { job_id: string; approved_entity_ids: number[] }
  >({
    mutationFn: async ({ job_id, approved_entity_ids }) => {
      const { data } = await api.post(`/redaction/jobs/${job_id}/approve`, {
        approved_entity_ids,
      });
      return data;
    },
    onSuccess: (data) => {
      qc.setQueryData(KEYS.job(data.id), data);
      qc.invalidateQueries({ queryKey: KEYS.jobs(data.document_id) });
    },
  });
}

/** Trigger PDF generation with redaction boxes applied. */
export function useApplyRedaction() {
  const qc = useQueryClient();
  return useMutation<RedactionJob, Error, { job_id: string }>({
    mutationFn: async ({ job_id }) => {
      const { data } = await api.post(`/redaction/jobs/${job_id}/apply`);
      return data;
    },
    onSuccess: (data) => {
      qc.setQueryData(KEYS.job(data.id), data);
      qc.invalidateQueries({ queryKey: KEYS.jobs(data.document_id) });
    },
  });
}
