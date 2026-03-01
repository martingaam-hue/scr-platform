"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

// ── Types ─────────────────────────────────────────────────────────────────────

export interface QAAnswer {
  id: string;
  question_id: string;
  body: string;
  is_official: boolean;
  author_id: string;
  created_at: string;
}

export interface QAQuestion {
  id: string;
  question_number: number;
  project_id: string;
  deal_room_id: string | null;
  asked_by_org_id: string;
  category: string;
  priority: string;
  status: string;
  title: string;
  body: string;
  assigned_team: string | null;
  sla_deadline: string | null;
  sla_breached: boolean;
  answered_at: string | null;
  created_at: string;
  answers: QAAnswer[];
}

export interface QAStats {
  total: number;
  open: number;
  answered: number;
  sla_breached: number;
  avg_response_hours: number | null;
}

// ── Hooks ─────────────────────────────────────────────────────────────────────

export function useProjectQuestions(projectId: string | undefined) {
  return useQuery<QAQuestion[]>({
    queryKey: ["qa", "project", projectId],
    queryFn: () =>
      api.get(`/qa/projects/${projectId}/questions`).then((r) => r.data),
    enabled: !!projectId,
  });
}

export function useCreateQuestion() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: {
      project_id: string;
      category: string;
      priority: string;
      title: string;
      body: string;
    }) =>
      api
        .post(`/qa/projects/${body.project_id}/questions`, body)
        .then((r) => r.data as QAQuestion),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["qa"] }),
  });
}

export function useAnswerQuestion() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      questionId,
      body,
      is_official,
    }: {
      questionId: string;
      body: string;
      is_official: boolean;
    }) =>
      api
        .post(`/qa/questions/${questionId}/answers`, { body, is_official })
        .then((r) => r.data as QAAnswer),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["qa"] }),
  });
}

export function useQAStats(projectId: string | undefined) {
  return useQuery<QAStats>({
    queryKey: ["qa", "stats", projectId],
    queryFn: () =>
      api.get(`/qa/projects/${projectId}/stats`).then((r) => r.data),
    enabled: !!projectId,
  });
}
