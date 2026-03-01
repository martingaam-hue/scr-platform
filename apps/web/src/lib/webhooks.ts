"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

// ── Types ─────────────────────────────────────────────────────────────────────

export interface WebhookSubscription {
  id: string;
  org_id: string;
  url: string;
  events: string[];
  is_active: boolean;
  failure_count: number;
  disabled_reason: string | null;
  description: string | null;
  created_at: string;
}

export interface WebhookDelivery {
  id: string;
  subscription_id: string;
  event_type: string;
  status: "pending" | "delivered" | "failed" | "retrying";
  response_status_code: number | null;
  attempts: number;
  next_retry_at: string | null;
  delivered_at: string | null;
  error_message: string | null;
  created_at: string;
}

export interface CreateWebhookPayload {
  url: string;
  secret: string;
  events: string[];
  description?: string;
}

export interface UpdateWebhookPayload {
  url?: string;
  events?: string[];
  description?: string;
  is_active?: boolean;
}

// ── Supported event types ──────────────────────────────────────────────────────

export const WEBHOOK_EVENTS: string[] = [
  "signal_score.computed",
  "signal_score.threshold_breach",
  "deal.stage_changed",
  "deal.screening_complete",
  "matching.new_match",
  "matching.score_updated",
  "monitoring.covenant_breach",
  "monitoring.kpi_variance",
  "dataroom.document_uploaded",
  "dataroom.document_accessed",
  "project.published",
  "project.status_changed",
];

// ── Query keys ────────────────────────────────────────────────────────────────

const WEBHOOKS_KEY = ["webhooks"] as const;
const WEBHOOK_KEY = (id: string) => ["webhooks", id] as const;
const DELIVERIES_KEY = (subscriptionId?: string) =>
  subscriptionId
    ? ["webhooks", subscriptionId, "deliveries"]
    : ["webhooks", "deliveries"];

// ── Hooks ─────────────────────────────────────────────────────────────────────

export function useWebhooks() {
  return useQuery({
    queryKey: WEBHOOKS_KEY,
    queryFn: async () => {
      const { data } = await api.get<WebhookSubscription[]>("/webhooks");
      return data;
    },
  });
}

export function useWebhook(id: string) {
  return useQuery({
    queryKey: WEBHOOK_KEY(id),
    queryFn: async () => {
      const { data } = await api.get<WebhookSubscription>(`/webhooks/${id}`);
      return data;
    },
    enabled: Boolean(id),
  });
}

export function useWebhookDeliveries(subscriptionId?: string) {
  return useQuery({
    queryKey: DELIVERIES_KEY(subscriptionId),
    queryFn: async () => {
      const url = subscriptionId
        ? `/webhooks/${subscriptionId}/deliveries`
        : "/webhooks/deliveries";
      const { data } = await api.get<WebhookDelivery[]>(url);
      return data;
    },
  });
}

export function useCreateWebhook() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: CreateWebhookPayload) => {
      const { data } = await api.post<WebhookSubscription>("/webhooks", payload);
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: WEBHOOKS_KEY });
    },
  });
}

export function useUpdateWebhook(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: UpdateWebhookPayload) => {
      const { data } = await api.put<WebhookSubscription>(
        `/webhooks/${id}`,
        payload
      );
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: WEBHOOKS_KEY });
      qc.invalidateQueries({ queryKey: WEBHOOK_KEY(id) });
    },
  });
}

export function useDeleteWebhook() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      await api.delete(`/webhooks/${id}`);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: WEBHOOKS_KEY });
    },
  });
}

export function useTestWebhook() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      id,
      event_type = "test.ping",
    }: {
      id: string;
      event_type?: string;
    }) => {
      const { data } = await api.post<WebhookDelivery>(
        `/webhooks/${id}/test`,
        { event_type }
      );
      return data;
    },
    onSuccess: (_data, variables) => {
      qc.invalidateQueries({ queryKey: DELIVERIES_KEY(variables.id) });
    },
  });
}

export function useEnableWebhook() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      const { data } = await api.post<WebhookSubscription>(
        `/webhooks/${id}/enable`
      );
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: WEBHOOKS_KEY });
    },
  });
}

export function useDisableWebhook() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      const { data } = await api.post<WebhookSubscription>(
        `/webhooks/${id}/disable`
      );
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: WEBHOOKS_KEY });
    },
  });
}
