"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useCallback, useRef, useState } from "react";
import { api } from "@/lib/api";

// ── Types ─────────────────────────────────────────────────────────────────────

export interface RalphMessage {
  id: string;
  role: "user" | "assistant" | "system" | "tool_call" | "tool_result";
  content: string;
  tool_calls?: Record<string, unknown> | null;
  tool_results?: Record<string, unknown> | null;
  model_used?: string | null;
  created_at: string;
}

export interface RalphConversation {
  id: string;
  title: string;
  context_type: string;
  context_entity_id?: string | null;
  created_at: string;
  updated_at: string;
}

export interface RalphConversationDetail extends RalphConversation {
  messages: RalphMessage[];
}

export interface ToolCallEvent {
  type: "tool_call";
  name: string;
  status: "running" | "done";
  result?: unknown;
}

export interface StreamEvent {
  type: "user_message" | "token" | "done" | "error" | "tool_call";
  content?: string;
  message_id?: string;
  name?: string;
  status?: string;
  result?: unknown;
  message?: string;
}

// ── Query key factory ─────────────────────────────────────────────────────────

export const ralphKeys = {
  all: ["ralph"] as const,
  conversations: () => [...ralphKeys.all, "conversations"] as const,
  conversation: (id: string) => [...ralphKeys.all, "conversation", id] as const,
};

// ── Hooks ─────────────────────────────────────────────────────────────────────

export function useConversations() {
  return useQuery({
    queryKey: ralphKeys.conversations(),
    queryFn: async (): Promise<RalphConversation[]> => {
      const { data } = await api.get("/ralph/conversations");
      return data;
    },
    staleTime: 30_000,
  });
}

export function useConversation(id: string | null) {
  return useQuery({
    queryKey: ralphKeys.conversation(id ?? ""),
    queryFn: async (): Promise<RalphConversationDetail> => {
      const { data } = await api.get(`/ralph/conversations/${id}`);
      return data;
    },
    enabled: !!id,
    staleTime: 10_000,
  });
}

export function useCreateConversation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: {
      title?: string;
      context_type?: string;
      context_entity_id?: string;
    }): Promise<RalphConversation> => {
      const { data } = await api.post("/ralph/conversations", body);
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ralphKeys.conversations() });
    },
  });
}

export function useDeleteConversation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: string): Promise<void> => {
      await api.delete(`/ralph/conversations/${id}`);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ralphKeys.conversations() });
    },
  });
}

// ── Streaming hook ────────────────────────────────────────────────────────────

export interface UseStreamMessageReturn {
  sendMessage: (content: string) => Promise<void>;
  isStreaming: boolean;
  activeToolCalls: string[];
  error: string | null;
}

export function useStreamMessage(
  conversationId: string | null,
  onToken: (token: string) => void,
  onDone: (messageId: string) => void,
  onUserMessage?: (messageId: string) => void,
): UseStreamMessageReturn {
  const [isStreaming, setIsStreaming] = useState(false);
  const [activeToolCalls, setActiveToolCalls] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const sendMessage = useCallback(
    async (content: string) => {
      if (!conversationId || isStreaming) return;

      abortRef.current?.abort();
      const controller = new AbortController();
      abortRef.current = controller;

      setIsStreaming(true);
      setActiveToolCalls([]);
      setError(null);

      try {
        const apiUrl =
          process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

        // Get the current auth token via the api interceptor
        // We need to make a raw fetch with the same Authorization header
        // that axios would use. Get the token from the axios default headers.
        const authHeader = (api.defaults.headers.common as Record<string, string>)["Authorization"] ?? "";

        const response = await fetch(
          `${apiUrl}/ralph/conversations/${conversationId}/stream`,
          {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              Authorization: authHeader,
            },
            body: JSON.stringify({ content }),
            signal: controller.signal,
          },
        );

        if (!response.ok) {
          throw new Error(`Stream request failed: ${response.status}`);
        }

        const reader = response.body!.getReader();
        const decoder = new TextDecoder();
        let buffer = "";

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split("\n");
          buffer = lines.pop() ?? "";

          for (const line of lines) {
            if (!line.startsWith("data: ")) continue;
            const raw = line.slice(6).trim();
            if (!raw) continue;

            try {
              const event: StreamEvent = JSON.parse(raw);
              switch (event.type) {
                case "user_message":
                  if (event.message_id) onUserMessage?.(event.message_id);
                  break;
                case "tool_call":
                  if (event.status === "running" && event.name) {
                    setActiveToolCalls((prev) => [...prev, event.name!]);
                  } else if (event.status === "done" && event.name) {
                    setActiveToolCalls((prev) =>
                      prev.filter((t) => t !== event.name),
                    );
                  }
                  break;
                case "token":
                  if (event.content) onToken(event.content);
                  break;
                case "done":
                  if (event.message_id) onDone(event.message_id);
                  break;
                case "error":
                  setError(event.message ?? "Unknown error");
                  break;
              }
            } catch {
              // Ignore parse errors on malformed chunks
            }
          }
        }
      } catch (err) {
        if ((err as Error).name !== "AbortError") {
          setError((err as Error).message ?? "Stream error");
        }
      } finally {
        setIsStreaming(false);
        setActiveToolCalls([]);
      }
    },
    [conversationId, isStreaming, onToken, onDone, onUserMessage],
  );

  return { sendMessage, isStreaming, activeToolCalls, error };
}
