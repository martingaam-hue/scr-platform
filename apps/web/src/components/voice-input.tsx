"use client";

/**
 * VoiceInput — audio file upload → Whisper transcription → AI extraction.
 *
 * Ally users can describe their project verbally; the component calls
 * POST /voice/process to transcribe and extract structured project fields,
 * then passes the result to the onExtracted callback.
 */

import { useRef, useState } from "react";
import { Mic, Upload, X, Loader2, CheckCircle, AlertCircle } from "lucide-react";
import { Button, cn } from "@scr/ui";
import {
  useProcessAudio,
  isValidAudioFile,
  MAX_FILE_SIZE_MB,
  type ExtractedProjectData,
} from "@/lib/voice-input";

// ── Props ─────────────────────────────────────────────────────────────────────

interface VoiceInputProps {
  onExtracted: (data: ExtractedProjectData, transcript: string) => void;
  className?: string;
}

// ── Component ─────────────────────────────────────────────────────────────────

export function VoiceInput({ onExtracted, className }: VoiceInputProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState(false);

  const { mutate: process, isPending } = useProcessAudio();

  const handleFileChange = (f: File | null) => {
    setError(null);
    setDone(false);
    if (!f) { setFile(null); return; }
    if (!isValidAudioFile(f)) {
      setError(`Unsupported file type or size (max ${MAX_FILE_SIZE_MB} MB). Try MP3, WAV, or M4A.`);
      setFile(null);
      return;
    }
    setFile(f);
  };

  const handleProcess = () => {
    if (!file) return;
    process(file, {
      onSuccess: (result) => {
        setDone(true);
        onExtracted(result.extracted, result.transcript);
      },
      onError: () => {
        setError("Transcription failed. Check your audio file and try again.");
      },
    });
  };

  return (
    <div className={cn("space-y-3", className)}>
      {/* Drop zone */}
      <div
        className={cn(
          "border-2 border-dashed rounded-lg p-5 text-center transition-all cursor-pointer",
          file
            ? "border-indigo-300 bg-indigo-50"
            : "border-gray-300 hover:border-indigo-300 hover:bg-gray-50"
        )}
        onClick={() => !isPending && inputRef.current?.click()}
        onDragOver={(e) => e.preventDefault()}
        onDrop={(e) => {
          e.preventDefault();
          handleFileChange(e.dataTransfer.files?.[0] ?? null);
        }}
      >
        <input
          ref={inputRef}
          type="file"
          accept="audio/*"
          className="hidden"
          onChange={(e) => handleFileChange(e.target.files?.[0] ?? null)}
        />
        {file ? (
          <div className="flex items-center justify-center gap-2">
            <Mic className="h-5 w-5 text-indigo-500" />
            <span className="text-sm font-medium text-indigo-700 truncate max-w-48">
              {file.name}
            </span>
            <button
              onClick={(e) => { e.stopPropagation(); handleFileChange(null); }}
              className="text-gray-400 hover:text-gray-600 ml-1"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        ) : (
          <div className="space-y-1">
            <Upload className="h-8 w-8 text-gray-400 mx-auto" />
            <p className="text-sm text-gray-600">
              Drop an audio file or <span className="text-indigo-600 font-medium">browse</span>
            </p>
            <p className="text-xs text-gray-400">
              MP3, WAV, M4A, OGG, WebM — up to {MAX_FILE_SIZE_MB} MB
            </p>
          </div>
        )}
      </div>

      {/* Error */}
      {error && (
        <div className="flex items-center gap-2 text-sm text-red-600">
          <AlertCircle className="h-4 w-4 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Success */}
      {done && !error && (
        <div className="flex items-center gap-2 text-sm text-green-700">
          <CheckCircle className="h-4 w-4 flex-shrink-0" />
          <span>Fields extracted — review and adjust below</span>
        </div>
      )}

      {/* Process button */}
      {file && !done && (
        <Button
          className="w-full"
          onClick={handleProcess}
          disabled={isPending}
        >
          {isPending ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin mr-2" />
              Transcribing…
            </>
          ) : (
            <>
              <Mic className="h-4 w-4 mr-2" />
              Extract Project Details
            </>
          )}
        </Button>
      )}

      {file && done && (
        <Button
          variant="outline"
          className="w-full"
          onClick={() => { handleFileChange(null); setDone(false); }}
        >
          Upload another recording
        </Button>
      )}
    </div>
  );
}
