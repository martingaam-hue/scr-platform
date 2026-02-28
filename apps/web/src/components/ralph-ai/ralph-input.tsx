"use client";

import React, { useRef, useState, useEffect, KeyboardEvent } from "react";
import { Send, Square } from "lucide-react";
import { cn } from "@scr/ui";

interface RalphInputProps {
  onSend: (content: string) => void;
  isStreaming: boolean;
  onStop?: () => void;
  initialValue?: string;
  onClearInitial?: () => void;
}

export function RalphInput({
  onSend,
  isStreaming,
  onStop,
  initialValue,
  onClearInitial,
}: RalphInputProps) {
  const [value, setValue] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Handle pre-populated suggestions
  useEffect(() => {
    if (initialValue) {
      setValue(initialValue);
      textareaRef.current?.focus();
      onClearInitial?.();
    }
  }, [initialValue, onClearInitial]);

  // Auto-resize textarea
  useEffect(() => {
    const ta = textareaRef.current;
    if (!ta) return;
    ta.style.height = "auto";
    ta.style.height = `${Math.min(ta.scrollHeight, 160)}px`;
  }, [value]);

  const handleSend = () => {
    const trimmed = value.trim();
    if (!trimmed || isStreaming) return;
    onSend(trimmed);
    setValue("");
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="border-t border-neutral-200 bg-white p-3 dark:border-neutral-800 dark:bg-neutral-900">
      <div className="flex items-end gap-2 rounded-xl border border-neutral-200 bg-neutral-50 px-3 py-2 focus-within:border-primary-400 focus-within:ring-1 focus-within:ring-primary-400 dark:border-neutral-700 dark:bg-neutral-800">
        <textarea
          ref={textareaRef}
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask Ralph anything..."
          rows={1}
          disabled={isStreaming}
          className="flex-1 resize-none bg-transparent text-sm text-neutral-900 placeholder-neutral-400 outline-none dark:text-neutral-100 dark:placeholder-neutral-500"
          style={{ maxHeight: "160px" }}
        />
        {isStreaming ? (
          <button
            onClick={onStop}
            className="flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-lg bg-neutral-200 text-neutral-600 transition-colors hover:bg-neutral-300 dark:bg-neutral-700 dark:text-neutral-400 dark:hover:bg-neutral-600"
            title="Stop generation"
          >
            <Square className="h-3.5 w-3.5" />
          </button>
        ) : (
          <button
            onClick={handleSend}
            disabled={!value.trim()}
            className={cn(
              "flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-lg transition-colors",
              value.trim()
                ? "bg-primary-600 text-white hover:bg-primary-700"
                : "bg-neutral-200 text-neutral-400 dark:bg-neutral-700 dark:text-neutral-500",
            )}
            title="Send message"
          >
            <Send className="h-3.5 w-3.5" />
          </button>
        )}
      </div>
      <p className="mt-1.5 px-1 text-[10px] text-neutral-400 dark:text-neutral-600">
        Enter to send · Shift+Enter for new line
      </p>
    </div>
  );
}
