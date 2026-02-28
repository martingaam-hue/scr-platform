"use client";

import React, { useRef, useState, useEffect, KeyboardEvent } from "react";
import { Send, Square, ChevronDown } from "lucide-react";
import { cn } from "@scr/ui";

export interface ContextSelection {
  type: "general" | "project" | "portfolio";
  id?: string;
  name?: string;
}

interface RalphInputProps {
  onSend: (content: string) => void;
  isStreaming: boolean;
  onStop?: () => void;
  initialValue?: string;
  onClearInitial?: () => void;
  context: ContextSelection;
  onContextChange: (ctx: ContextSelection) => void;
  projects: Array<{ id: string; name: string }>;
  portfolios: Array<{ id: string; name: string }>;
}

export function RalphInput({
  onSend,
  isStreaming,
  onStop,
  initialValue,
  onClearInitial,
  context,
  onContextChange,
  projects,
  portfolios,
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

  const handleTypeChange = (type: ContextSelection["type"]) => {
    if (type === "general") {
      onContextChange({ type: "general" });
    } else if (type === "project") {
      const first = projects[0];
      onContextChange({ type: "project", id: first?.id, name: first?.name });
    } else {
      const first = portfolios[0];
      onContextChange({ type: "portfolio", id: first?.id, name: first?.name });
    }
  };

  const handleEntityChange = (id: string) => {
    const list = context.type === "project" ? projects : portfolios;
    const entity = list.find((e) => e.id === id);
    onContextChange({ ...context, id, name: entity?.name });
  };

  const showEntitySelect =
    context.type !== "general" &&
    (context.type === "project" ? projects : portfolios).length > 0;

  return (
    <div className="border-t border-neutral-200 bg-white p-3 dark:border-neutral-800 dark:bg-neutral-900">
      {/* Context selector row */}
      <div className="mb-2 flex items-center gap-1.5">
        <span className="text-[10px] font-medium uppercase tracking-wider text-neutral-400 dark:text-neutral-500">
          Context
        </span>
        <div className="relative">
          <select
            value={context.type}
            onChange={(e) => handleTypeChange(e.target.value as ContextSelection["type"])}
            className="appearance-none rounded-md border border-neutral-200 bg-neutral-50 py-0.5 pl-2 pr-5 text-xs text-neutral-700 focus:border-primary-400 focus:outline-none dark:border-neutral-700 dark:bg-neutral-800 dark:text-neutral-300"
          >
            <option value="general">General</option>
            {projects.length > 0 && <option value="project">Project</option>}
            {portfolios.length > 0 && <option value="portfolio">Portfolio</option>}
          </select>
          <ChevronDown className="pointer-events-none absolute right-1 top-1/2 h-3 w-3 -translate-y-1/2 text-neutral-400" />
        </div>

        {showEntitySelect && (
          <div className="relative">
            <select
              value={context.id ?? ""}
              onChange={(e) => handleEntityChange(e.target.value)}
              className="appearance-none rounded-md border border-neutral-200 bg-neutral-50 py-0.5 pl-2 pr-5 text-xs text-neutral-700 focus:border-primary-400 focus:outline-none dark:border-neutral-700 dark:bg-neutral-800 dark:text-neutral-300 max-w-[160px]"
            >
              {(context.type === "project" ? projects : portfolios).map((e) => (
                <option key={e.id} value={e.id}>
                  {e.name}
                </option>
              ))}
            </select>
            <ChevronDown className="pointer-events-none absolute right-1 top-1/2 h-3 w-3 -translate-y-1/2 text-neutral-400" />
          </div>
        )}

        {context.type !== "general" && context.id && (
          <span className="rounded-full bg-primary-100 px-2 py-0.5 text-[10px] font-medium text-primary-700 dark:bg-primary-900/30 dark:text-primary-300">
            Scoped
          </span>
        )}
      </div>

      {/* Textarea + send */}
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
