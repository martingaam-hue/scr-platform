"use client";

import React, { useState } from "react";
import { ThumbsUp, ThumbsDown, MessageSquare } from "lucide-react";
import { cn } from "@scr/ui";
import { api } from "@/lib/api";

// ── Types ─────────────────────────────────────────────────────────────────────

interface AIFeedbackProps {
  /** ID from the AITaskLog table (task_log_id on the response). */
  taskLogId?: string | null;
  /** task_type string matching the AI gateway task type (e.g. "score_quality"). */
  taskType: string;
  /** Optional entity reference to attach to the feedback record. */
  entityType?: string;
  entityId?: string;
  /** Compact mode shows only icons, no label text. */
  compact?: boolean;
  className?: string;
}

// ── Component ─────────────────────────────────────────────────────────────────

export function AIFeedback({
  taskLogId,
  taskType,
  entityType,
  entityId,
  compact = false,
  className,
}: AIFeedbackProps) {
  const [submitted, setSubmitted] = useState<"up" | "down" | null>(null);
  const [showComment, setShowComment] = useState(false);
  const [comment, setComment] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function submit(rating: 1 | -1, userComment?: string) {
    if (submitting || submitted) return;
    setSubmitting(true);
    try {
      await api.post("/ai-feedback/rate", {
        task_log_id: taskLogId ?? undefined,
        task_type: taskType,
        entity_type: entityType ?? undefined,
        entity_id: entityId ?? undefined,
        rating,
        comment: userComment ?? undefined,
      });
      setSubmitted(rating === 1 ? "up" : "down");
      setShowComment(false);
    } catch {
      // Silently ignore — feedback is non-critical
    } finally {
      setSubmitting(false);
    }
  }

  function handleThumbsDown() {
    if (submitted || submitting) return;
    // Show comment field before submitting negative feedback
    setShowComment(true);
  }

  async function handleCommentSubmit() {
    await submit(-1, comment || undefined);
  }

  if (submitted) {
    return (
      <div className={cn("flex items-center gap-1 text-xs text-neutral-400", className)}>
        <span>Thanks for your feedback</span>
      </div>
    );
  }

  return (
    <div className={cn("flex flex-col gap-2", className)}>
      <div className="flex items-center gap-1">
        {!compact && (
          <span className="text-xs text-neutral-400 mr-1">Was this helpful?</span>
        )}

        {/* Thumbs up */}
        <button
          onClick={() => submit(1)}
          disabled={submitting}
          title="Helpful"
          className={cn(
            "rounded p-1 text-neutral-400 transition-colors hover:bg-neutral-100 hover:text-green-600 dark:hover:bg-neutral-800 dark:hover:text-green-400",
            submitting && "cursor-wait opacity-50"
          )}
        >
          <ThumbsUp className="h-3.5 w-3.5" />
        </button>

        {/* Thumbs down */}
        <button
          onClick={handleThumbsDown}
          disabled={submitting}
          title="Not helpful"
          className={cn(
            "rounded p-1 text-neutral-400 transition-colors hover:bg-neutral-100 hover:text-red-600 dark:hover:bg-neutral-800 dark:hover:text-red-400",
            submitting && "cursor-wait opacity-50"
          )}
        >
          <ThumbsDown className="h-3.5 w-3.5" />
        </button>
      </div>

      {/* Optional comment for negative feedback */}
      {showComment && (
        <div className="flex flex-col gap-1.5 rounded-md border border-neutral-200 bg-neutral-50 p-2 dark:border-neutral-700 dark:bg-neutral-800/50">
          <label className="text-xs font-medium text-neutral-600 dark:text-neutral-300">
            What could be improved? (optional)
          </label>
          <textarea
            value={comment}
            onChange={(e) => setComment(e.target.value)}
            placeholder="e.g. Incorrect score, missing context..."
            rows={2}
            className="w-full resize-none rounded border border-neutral-200 bg-white px-2 py-1 text-xs text-neutral-800 placeholder:text-neutral-400 focus:outline-none focus:ring-1 focus:ring-primary-500 dark:border-neutral-700 dark:bg-neutral-900 dark:text-neutral-100"
          />
          <div className="flex gap-1.5">
            <button
              onClick={handleCommentSubmit}
              disabled={submitting}
              className="rounded bg-neutral-800 px-2.5 py-1 text-xs font-medium text-white hover:bg-neutral-700 disabled:opacity-50 dark:bg-neutral-200 dark:text-neutral-900 dark:hover:bg-neutral-100"
            >
              Submit
            </button>
            <button
              onClick={() => submit(-1)}
              disabled={submitting}
              className="rounded px-2 py-1 text-xs text-neutral-500 hover:text-neutral-700 dark:hover:text-neutral-300"
            >
              Skip
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

// ── Edit tracking hook ────────────────────────────────────────────────────────

/**
 * Call this hook when a user saves edits to AI-generated content.
 * Automatically computes and records the edit signal.
 *
 * @example
 * const trackEdit = useAIEditTracking("generate_memo", "project", projectId)
 * // ...in save handler:
 * trackEdit(originalContent, editedContent)
 */
export function useAIEditTracking(
  taskType: string,
  entityType?: string,
  entityId?: string,
  taskLogId?: string | null
) {
  return async function trackEdit(
    originalContent: string,
    editedContent: string
  ) {
    if (originalContent === editedContent) return;
    try {
      await api.post("/ai-feedback/track-edit", {
        task_log_id: taskLogId ?? undefined,
        task_type: taskType,
        entity_type: entityType ?? undefined,
        entity_id: entityId ?? undefined,
        original_content: originalContent,
        edited_content: editedContent,
      });
    } catch {
      // Non-critical
    }
  };
}

/**
 * Call when a user clicks "Use this" / "Accept" on an AI output without editing.
 */
export function useAIAcceptTracking(
  taskType: string,
  entityType?: string,
  entityId?: string,
  taskLogId?: string | null
) {
  return async function trackAccept() {
    try {
      await api.post("/ai-feedback/track-accept", {
        task_log_id: taskLogId ?? undefined,
        task_type: taskType,
        entity_type: entityType ?? undefined,
        entity_id: entityId ?? undefined,
      });
    } catch {
      // Non-critical
    }
  };
}
