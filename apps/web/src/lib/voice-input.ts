/**
 * Voice Input — hooks and helpers for audio transcription + AI extraction.
 */

import { useMutation } from "@tanstack/react-query";
import { api } from "@/lib/api";

// ── Types ──────────────────────────────────────────────────────────────────

export interface ExtractedProjectData {
  name?: string;
  description?: string;
  project_type?: string;
  location?: string;
  capacity_mw?: number;
  budget_total?: number;
  timeline_months?: number;
  [key: string]: unknown;
}

export interface TranscribeResponse {
  transcript: string;
}

export interface ProcessResponse {
  transcript: string;
  extracted: ExtractedProjectData;
}

// ── Hooks ───────────────────────────────────────────────────────────────────

export function useTranscribeAudio() {
  return useMutation({
    mutationFn: async (file: File) => {
      const formData = new FormData();
      formData.append("file", file);
      const { data } = await api.post<TranscribeResponse>("/voice/transcribe", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      return data;
    },
  });
}

export function useExtractFromTranscript() {
  return useMutation({
    mutationFn: async (transcript: string) => {
      const { data } = await api.post<{ extracted: ExtractedProjectData }>("/voice/extract", {
        transcript,
      });
      return data;
    },
  });
}

export function useProcessAudio() {
  return useMutation({
    mutationFn: async (file: File) => {
      const formData = new FormData();
      formData.append("file", file);
      const { data } = await api.post<ProcessResponse>("/voice/process", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      return data;
    },
  });
}

// ── Recording helpers ───────────────────────────────────────────────────────

export const SUPPORTED_AUDIO_TYPES = [
  "audio/mpeg",
  "audio/mp3",
  "audio/wav",
  "audio/x-wav",
  "audio/mp4",
  "audio/m4a",
  "audio/webm",
  "audio/ogg",
];

export const MAX_FILE_SIZE_MB = 25;

export function isValidAudioFile(file: File): boolean {
  return SUPPORTED_AUDIO_TYPES.includes(file.type) && file.size <= MAX_FILE_SIZE_MB * 1024 * 1024;
}

export function formatDuration(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${s.toString().padStart(2, "0")}`;
}
