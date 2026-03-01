"use client";

import { useMutation } from "@tanstack/react-query";
import { api } from "@/lib/api";

// ── Types ─────────────────────────────────────────────────────────────────────

export interface ExtractedProjectData {
  name: string | null;
  description: string | null;
  project_type: string | null;
  location: string | null;
  capacity_mw: number | null;
  total_investment_needed: number | null;
  budget_total: number | null;
  currency: string | null;
  stage: string | null;
  technology: string | null;
  irr_target: number | null;
  timeline_months: number | null;
}

// ── Constants ─────────────────────────────────────────────────────────────────

export const MAX_FILE_SIZE_MB = 25;

const ALLOWED_AUDIO_TYPES = new Set([
  "audio/mpeg", "audio/mp3", "audio/wav", "audio/x-wav",
  "audio/mp4", "audio/m4a", "audio/x-m4a", "audio/ogg", "audio/webm",
]);

export function isValidAudioFile(file: File): boolean {
  return ALLOWED_AUDIO_TYPES.has(file.type) && file.size <= MAX_FILE_SIZE_MB * 1024 * 1024;
}

export interface ProcessResponse {
  transcript: string;
  extracted: ExtractedProjectData;
}

// ── Hooks ─────────────────────────────────────────────────────────────────────

export function useProcessAudio() {
  return useMutation({
    mutationFn: async (file: File): Promise<ProcessResponse> => {
      const formData = new FormData();
      formData.append("file", file);
      const { data } = await api.post<ProcessResponse>("/voice/process", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      return data;
    },
  });
}
