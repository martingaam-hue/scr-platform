"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

// ── Types ─────────────────────────────────────────────────────────────────────

export interface DealRoom {
  id: string;
  name: string;
  project_id: string;
  status: string;
  created_by: string;
  settings: {
    nda_required?: boolean;
    download_restricted?: boolean;
    expires_at?: string | null;
  };
  members: DealRoomMember[];
  created_at: string;
}

export interface DealRoomMember {
  id: string;
  room_id: string;
  user_id: string | null;
  email: string | null;
  role: string;
  org_name: string | null;
  permissions: Record<string, boolean>;
  invited_at: string;
  joined_at: string | null;
  nda_signed_at: string | null;
}

export interface DealRoomMessage {
  id: string;
  room_id: string;
  user_id: string;
  parent_id: string | null;
  content: string;
  mentions: string[];
  created_at: string;
}

export interface DealRoomActivity {
  id: string;
  room_id: string;
  user_id: string;
  activity_type: string;
  entity_type: string | null;
  entity_id: string | null;
  description: string | null;
  created_at: string;
}

// ── Hooks ─────────────────────────────────────────────────────────────────────

export function useDealRooms() {
  return useQuery<DealRoom[]>({
    queryKey: ["deal-rooms"],
    queryFn: () => api.get("/deal-rooms/").then((r) => r.data),
  });
}

export function useDealRoom(roomId: string) {
  return useQuery<DealRoom>({
    queryKey: ["deal-room", roomId],
    queryFn: () => api.get(`/deal-rooms/${roomId}`).then((r) => r.data),
    enabled: !!roomId,
  });
}

export function useRoomMessages(roomId: string | null) {
  return useQuery<DealRoomMessage[]>({
    queryKey: ["deal-room-messages", roomId],
    queryFn: () =>
      api.get(`/deal-rooms/${roomId}/messages`).then((r) => r.data),
    enabled: !!roomId,
  });
}

export function useRoomActivity(roomId: string | null) {
  return useQuery<DealRoomActivity[]>({
    queryKey: ["deal-room-activity", roomId],
    queryFn: () =>
      api.get(`/deal-rooms/${roomId}/activity`).then((r) => r.data),
    enabled: !!roomId,
  });
}

export function useCreateRoom() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: Record<string, unknown>) =>
      api.post("/deal-rooms/", body).then((r) => r.data as DealRoom),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["deal-rooms"] }),
  });
}

export function useInviteMember(roomId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { email: string; role: string; org_name?: string }) =>
      api.post(`/deal-rooms/${roomId}/invite`, body).then((r) => r.data),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: ["deal-room", roomId] }),
  });
}

export function useSendMessage(roomId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (content: string) =>
      api
        .post(`/deal-rooms/${roomId}/messages`, { content })
        .then((r) => r.data),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: ["deal-room-messages", roomId] }),
  });
}

export function useCloseRoom() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (roomId: string) =>
      api.post(`/deal-rooms/${roomId}/close`).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["deal-rooms"] }),
  });
}
