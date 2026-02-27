/**
 * Collaboration types and React Query hooks.
 *
 * Types mirror the FastAPI Pydantic schemas for comments and activity.
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

// ── Types ──────────────────────────────────────────────────────────────────

export interface CommentAuthor {
  user_id: string;
  full_name: string;
  avatar_url: string | null;
}

export interface CommentResponse {
  id: string;
  org_id: string;
  user_id: string;
  author: CommentAuthor;
  entity_type: string;
  entity_id: string;
  parent_id: string | null;
  content: string;
  mentions: Record<string, unknown> | null;
  is_resolved: boolean;
  created_at: string;
  replies: CommentResponse[];
}

export interface CommentListResponse {
  items: CommentResponse[];
  total: number;
}

export interface ActivityResponse {
  id: string;
  org_id: string;
  user_id: string | null;
  user_name: string | null;
  user_avatar: string | null;
  entity_type: string;
  entity_id: string;
  action: string;
  description: string;
  changes: Record<string, unknown> | null;
  created_at: string;
}

export interface ActivityListResponse {
  items: ActivityResponse[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

// ── Query Key Factories ────────────────────────────────────────────────────

export const commentKeys = {
  all: ["comments"] as const,
  entity: (entityType: string, entityId: string) =>
    [...commentKeys.all, entityType, entityId] as const,
};

export const activityKeys = {
  all: ["activity"] as const,
  entity: (entityType: string, entityId: string) =>
    [...activityKeys.all, entityType, entityId] as const,
  feed: (page?: number) => [...activityKeys.all, "feed", page ?? 1] as const,
};

// ── Comment Hooks ──────────────────────────────────────────────────────────

export function useComments(entityType: string, entityId: string) {
  return useQuery({
    queryKey: commentKeys.entity(entityType, entityId),
    queryFn: async () => {
      const { data } = await api.get<CommentListResponse>(
        "/collaboration/comments",
        { params: { entity_type: entityType, entity_id: entityId } }
      );
      return data;
    },
    enabled: !!entityType && !!entityId,
  });
}

export function useCreateComment() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: {
      entity_type: string;
      entity_id: string;
      content: string;
      parent_comment_id?: string;
    }) => {
      const { data } = await api.post<CommentResponse>(
        "/collaboration/comments",
        payload
      );
      return data;
    },
    onSuccess: (_data, vars) => {
      qc.invalidateQueries({
        queryKey: commentKeys.entity(vars.entity_type, vars.entity_id),
      });
    },
  });
}

export function useEditComment() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      commentId,
      content,
    }: {
      commentId: string;
      content: string;
      entityType: string;
      entityId: string;
    }) => {
      const { data } = await api.put<CommentResponse>(
        `/collaboration/comments/${commentId}`,
        { content }
      );
      return data;
    },
    onSuccess: (_data, vars) => {
      qc.invalidateQueries({
        queryKey: commentKeys.entity(vars.entityType, vars.entityId),
      });
    },
  });
}

export function useDeleteComment() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      commentId,
    }: {
      commentId: string;
      entityType: string;
      entityId: string;
    }) => {
      await api.delete(`/collaboration/comments/${commentId}`);
    },
    onSuccess: (_data, vars) => {
      qc.invalidateQueries({
        queryKey: commentKeys.entity(vars.entityType, vars.entityId),
      });
    },
  });
}

export function useResolveComment() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      commentId,
    }: {
      commentId: string;
      entityType: string;
      entityId: string;
    }) => {
      const { data } = await api.post<CommentResponse>(
        `/collaboration/comments/${commentId}/resolve`
      );
      return data;
    },
    onSuccess: (_data, vars) => {
      qc.invalidateQueries({
        queryKey: commentKeys.entity(vars.entityType, vars.entityId),
      });
    },
  });
}

// ── Activity Hooks ─────────────────────────────────────────────────────────

export function useEntityActivity(
  entityType: string,
  entityId: string,
  page = 1
) {
  return useQuery({
    queryKey: activityKeys.entity(entityType, entityId),
    queryFn: async () => {
      const { data } = await api.get<ActivityListResponse>(
        "/collaboration/activity",
        {
          params: {
            entity_type: entityType,
            entity_id: entityId,
            page,
          },
        }
      );
      return data;
    },
    enabled: !!entityType && !!entityId,
  });
}

export function useActivityFeed(page = 1) {
  return useQuery({
    queryKey: activityKeys.feed(page),
    queryFn: async () => {
      const { data } = await api.get<ActivityListResponse>(
        "/collaboration/activity/feed",
        { params: { page } }
      );
      return data;
    },
  });
}

// ── Helpers ────────────────────────────────────────────────────────────────

export function timeAgo(dateStr: string): string {
  const now = Date.now();
  const then = new Date(dateStr).getTime();
  const seconds = Math.floor((now - then) / 1000);

  if (seconds < 60) return "just now";
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  if (days < 30) return `${days}d ago`;
  const months = Math.floor(days / 30);
  if (months < 12) return `${months}mo ago`;
  return `${Math.floor(months / 12)}y ago`;
}
