/**
 * Legal Document Manager — types and React Query hooks.
 */

import {
  useQuery,
  useMutation,
  useQueryClient,
} from "@tanstack/react-query";
import { api } from "@/lib/api";

// ── Types ───────────────────────────────────────────────────────────────────

export interface QuestionnaireField {
  id: string;
  type: "text" | "textarea" | "select" | "number" | "date" | "boolean";
  label: string;
  required?: boolean;
  options?: string[];
  placeholder?: string;
}

export interface QuestionnaireSection {
  id: string;
  title: string;
  fields: QuestionnaireField[];
}

export interface Questionnaire {
  sections: QuestionnaireSection[];
}

export interface TemplateListItem {
  id: string;
  name: string;
  doc_type: string;
  description: string;
  estimated_pages: number;
}

export interface TemplateDetail extends TemplateListItem {
  questionnaire: Questionnaire;
}

export interface LegalDocumentResponse {
  id: string;
  title: string;
  doc_type: string;
  status: string;
  template_id: string | null;
  project_id: string | null;
  content: string;
  s3_key: string | null;
  version: number;
  signed_date: string | null;
  expiry_date: string | null;
  questionnaire_answers: Record<string, unknown> | null;
  generation_status: string | null;
  download_url: string | null;
  created_at: string;
  updated_at: string;
}

export interface LegalDocumentListResponse {
  items: LegalDocumentResponse[];
  total: number;
}

export interface GenerateDocumentResponse {
  document_id: string;
  status: string;
  message: string;
}

export interface ReviewResponse {
  review_id: string;
  status: string;
  message: string;
}

export interface ClauseAnalysis {
  clause_type: string;
  text_excerpt: string;
  risk_level: "low" | "medium" | "high" | "critical";
  issue: string | null;
  recommendation: string | null;
}

export interface ReviewResultResponse {
  review_id: string;
  document_id: string | null;
  mode: string;
  jurisdiction: string;
  status: string;
  overall_risk_score: number | null;
  summary: string | null;
  clause_analyses: ClauseAnalysis[];
  missing_clauses: string[];
  jurisdiction_issues: string[];
  recommendations: string[];
  model_used: string | null;
  created_at: string;
}

// ── Query Keys ──────────────────────────────────────────────────────────────

export const legalKeys = {
  all: ["legal"] as const,
  templates: () => [...legalKeys.all, "templates"] as const,
  template: (id: string) => [...legalKeys.all, "templates", id] as const,
  documents: (page?: number) => [...legalKeys.all, "documents", page ?? 1] as const,
  document: (id: string) => [...legalKeys.all, "documents", id] as const,
  review: (id: string) => [...legalKeys.all, "review", id] as const,
};

// ── Hooks ───────────────────────────────────────────────────────────────────

export function useTemplates() {
  return useQuery({
    queryKey: legalKeys.templates(),
    queryFn: () =>
      api.get<TemplateListItem[]>("/legal/templates").then((r) => r.data),
  });
}

export function useTemplate(templateId: string | null) {
  return useQuery({
    queryKey: legalKeys.template(templateId ?? ""),
    queryFn: () =>
      api
        .get<TemplateDetail>(`/legal/templates/${templateId}`)
        .then((r) => r.data),
    enabled: !!templateId,
  });
}

export function useLegalDocuments(page = 1) {
  return useQuery({
    queryKey: legalKeys.documents(page),
    queryFn: () =>
      api
        .get<LegalDocumentListResponse>(`/legal/documents?page=${page}`)
        .then((r) => r.data),
  });
}

export function useLegalDocument(documentId: string | null) {
  return useQuery({
    queryKey: legalKeys.document(documentId ?? ""),
    queryFn: () =>
      api
        .get<LegalDocumentResponse>(`/legal/documents/${documentId}`)
        .then((r) => r.data),
    enabled: !!documentId,
    refetchInterval: (query) => {
      const data = query.state.data;
      if (!data) return false;
      const gs = data.generation_status;
      return gs === "pending" || gs === "generating" ? 3000 : false;
    },
  });
}

export function useCreateLegalDocument() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: {
      template_id: string;
      title: string;
      project_id?: string;
    }) =>
      api
        .post<LegalDocumentResponse>("/legal/documents", body)
        .then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: legalKeys.documents() });
    },
  });
}

export function useUpdateDocumentAnswers() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      documentId,
      answers,
    }: {
      documentId: string;
      answers: Record<string, unknown>;
    }) =>
      api
        .put<LegalDocumentResponse>(`/legal/documents/${documentId}`, {
          questionnaire_answers: answers,
        })
        .then((r) => r.data),
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: legalKeys.document(data.id) });
    },
  });
}

export function useGenerateDocument() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      documentId,
      format = "html",
    }: {
      documentId: string;
      format?: string;
    }) =>
      api
        .post<GenerateDocumentResponse>(
          `/legal/documents/${documentId}/generate`,
          { format }
        )
        .then((r) => r.data),
    onSuccess: (_data, vars) => {
      qc.invalidateQueries({ queryKey: legalKeys.document(vars.documentId) });
    },
  });
}

export function useReviewDocument() {
  return useMutation({
    mutationFn: (body: {
      document_id?: string;
      document_text?: string;
      mode?: string;
      jurisdiction?: string;
    }) =>
      api.post<ReviewResponse>("/legal/review", body).then((r) => r.data),
  });
}

export function useReviewResult(reviewId: string | null) {
  return useQuery({
    queryKey: legalKeys.review(reviewId ?? ""),
    queryFn: () =>
      api
        .get<ReviewResultResponse>(`/legal/review/${reviewId}`)
        .then((r) => r.data),
    enabled: !!reviewId,
    refetchInterval: (query) => {
      const data = query.state.data;
      if (!data) return 3000;
      return data.status === "pending" || data.status === "processing"
        ? 3000
        : false;
    },
  });
}

// ── Helpers ─────────────────────────────────────────────────────────────────

export const DOC_TYPE_LABELS: Record<string, string> = {
  term_sheet: "Term Sheet",
  subscription_agreement: "Subscription Agreement",
  spv_incorporation: "SPV Incorporation",
  nda: "NDA",
  side_letter: "Side Letter",
  amendment: "Amendment",
};

export const DOC_STATUS_LABELS: Record<string, string> = {
  draft: "Draft",
  review: "Under Review",
  sent: "Sent",
  signed: "Signed",
  executed: "Executed",
  expired: "Expired",
};

export function docStatusBadge(
  status: string
): "neutral" | "warning" | "success" | "error" {
  switch (status) {
    case "signed":
    case "executed":
      return "success";
    case "review":
    case "sent":
      return "warning";
    case "expired":
      return "error";
    default:
      return "neutral";
  }
}

export function clauseRiskBadge(
  risk: string
): "error" | "warning" | "neutral" | "success" {
  switch (risk) {
    case "critical":
    case "high":
      return "error";
    case "medium":
      return "warning";
    case "low":
      return "success";
    default:
      return "neutral";
  }
}

export const REVIEW_MODE_LABELS: Record<string, string> = {
  comprehensive: "Comprehensive Review",
  risk_focused: "Risk-Focused",
  compliance: "Compliance Check",
  negotiation: "Negotiation Analysis",
};

export const SUPPORTED_JURISDICTIONS = [
  "England & Wales",
  "New York",
  "Delaware",
  "Singapore",
  "Netherlands",
  "Germany",
  "France",
  "Cayman Islands",
  "British Virgin Islands",
  "Luxembourg",
  "Ireland",
  "Other",
];
