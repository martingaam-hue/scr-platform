"use client";

import React, { useCallback, useEffect, useRef, useState } from "react";
import { Bot, User, Loader2, Wrench, ExternalLink } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { useQuery } from "@tanstack/react-query";
import { cn } from "@scr/ui";
import {
  RalphMessage,
  useConversation,
  useStreamMessage,
} from "@/lib/ralph";
import { api } from "@/lib/api";
import { RalphInput, type ContextSelection } from "./ralph-input";
import { RalphSuggestions } from "./ralph-suggestions";

interface RalphChatProps {
  conversationId: string;
  initialMessage?: string;
  onClearInitial?: () => void;
}

interface StreamingMessage {
  id: "streaming";
  role: "assistant";
  content: string;
  created_at: string;
}

// ── Action button extraction ───────────────────────────────────────────────

interface ActionButton {
  label: string;
  href: string;
}

function extractActionButtons(msg: RalphMessage): ActionButton[] {
  const results: Array<{ tool: string; result: Record<string, unknown> }> =
    (msg.tool_results as { results?: Array<{ tool: string; result: Record<string, unknown> }> })?.results ?? [];

  const buttons: ActionButton[] = [];
  const seen = new Set<string>();

  const add = (label: string, href: string) => {
    if (!seen.has(href)) {
      seen.add(href);
      buttons.push({ label, href });
    }
  };

  for (const { tool, result } of results) {
    if (!result || typeof result !== "object" || "error" in result) continue;

    switch (tool) {
      case "get_project_details":
      case "deep_dive_project":
      case "deal_readiness_check": {
        const projectId = (result as { id?: string; project?: { id?: string } }).id
          ?? (result as { project?: { id?: string } }).project?.id;
        if (projectId) add("Open Project", `/projects/${projectId}`);
        break;
      }
      case "get_signal_score":
      case "get_improvement_plan": {
        const projectId = (result as { project_id?: string }).project_id;
        if (projectId) add("Open Project", `/projects/${projectId}`);
        break;
      }
      case "find_matching_investors":
      case "find_matching_projects":
        add("View Matches", `/matching`);
        break;
      case "run_valuation":
        add("View Valuations", `/valuations`);
        break;
      case "generate_report_section":
        add("Generate Report", `/reports`);
        break;
      case "get_portfolio_metrics":
      case "portfolio_health_check":
        add("View Portfolio", `/portfolio`);
        break;
      case "get_risk_assessment":
      case "get_risk_mitigation_strategies":
        add("View Risk", `/risk`);
        break;
    }
  }

  return buttons;
}

// ── Context-aware message sender ───────────────────────────────────────────

function buildMessageContent(content: string, ctx: ContextSelection): string {
  if (ctx.type === "general" || !ctx.id) return content;
  const label = ctx.type === "project" ? "Project" : "Portfolio";
  return `[Ralph, focus your analysis on ${label} "${ctx.name ?? ctx.id}" (ID: ${ctx.id})]\n\n${content}`;
}

// ── Component ──────────────────────────────────────────────────────────────

export function RalphChat({
  conversationId,
  initialMessage,
  onClearInitial,
}: RalphChatProps) {
  const { data: conversation, refetch } = useConversation(conversationId);
  const [streamingContent, setStreamingContent] = useState<string | null>(null);
  const [activeToolCalls, setActiveToolCalls] = useState<string[]>([]);
  const [context, setContext] = useState<ContextSelection>({ type: "general" });
  const bottomRef = useRef<HTMLDivElement>(null);

  // Fetch projects and portfolios for context selector
  const { data: projectsData } = useQuery({
    queryKey: ["ralph-context-projects"],
    queryFn: () => api.get("/projects").then((r) => r.data.items ?? []) as Promise<Array<{ id: string; name: string }>>,
    staleTime: 5 * 60_000,
  });
  const { data: portfoliosData } = useQuery({
    queryKey: ["ralph-context-portfolios"],
    queryFn: () => api.get("/portfolio").then((r) => r.data.items ?? []) as Promise<Array<{ id: string; name: string }>>,
    staleTime: 5 * 60_000,
  });

  const handleToken = useCallback((token: string) => {
    setStreamingContent((prev) => (prev ?? "") + token);
  }, []);

  const handleDone = useCallback(
    (_messageId: string) => {
      setStreamingContent(null);
      setActiveToolCalls([]);
      refetch();
    },
    [refetch],
  );

  const { sendMessage, isStreaming, activeToolCalls: streamToolCalls } =
    useStreamMessage(conversationId, handleToken, handleDone);

  useEffect(() => {
    setActiveToolCalls(streamToolCalls);
  }, [streamToolCalls]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [conversation?.messages, streamingContent, activeToolCalls]);

  const handleSend = useCallback(
    (content: string) => {
      sendMessage(buildMessageContent(content, context));
    },
    [sendMessage, context],
  );

  const messages: (RalphMessage | StreamingMessage)[] = [
    ...(conversation?.messages ?? []),
    ...(streamingContent !== null
      ? [
          {
            id: "streaming" as const,
            role: "assistant" as const,
            content: streamingContent,
            created_at: new Date().toISOString(),
          },
        ]
      : []),
  ];

  const showSuggestions =
    messages.filter((m) => m.role === "user").length === 0 && !isStreaming;

  return (
    <div className="flex h-full flex-col">
      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-4">
        {messages.length === 0 && !isStreaming && (
          <div className="flex h-full flex-col items-center justify-center gap-3 text-center">
            <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-primary-100 dark:bg-primary-900/30">
              <Bot className="h-6 w-6 text-primary-600 dark:text-primary-400" />
            </div>
            <div>
              <p className="font-medium text-neutral-900 dark:text-neutral-100">
                Ask Ralph anything
              </p>
              <p className="mt-1 text-sm text-neutral-500 dark:text-neutral-400">
                I can analyze your projects, portfolio, documents, and more.
              </p>
            </div>
          </div>
        )}

        <div className="space-y-4">
          {messages
            .filter((m) => m.role === "user" || m.role === "assistant")
            .map((message) => (
              <MessageBubble key={message.id} message={message} />
            ))}

          {/* Tool call indicators */}
          {activeToolCalls.map((toolName) => (
            <ToolCallIndicator key={toolName} name={toolName} />
          ))}
        </div>

        <div ref={bottomRef} />
      </div>

      {/* Suggestions (only when conversation is empty) */}
      {showSuggestions && (
        <RalphSuggestions onSelect={(s) => handleSend(s)} />
      )}

      {/* Input */}
      <RalphInput
        onSend={handleSend}
        isStreaming={isStreaming}
        initialValue={initialMessage}
        onClearInitial={onClearInitial}
        context={context}
        onContextChange={setContext}
        projects={projectsData ?? []}
        portfolios={portfoliosData ?? []}
      />
    </div>
  );
}

// ── Sub-components ────────────────────────────────────────────────────────

interface MessageBubbleProps {
  message: RalphMessage | StreamingMessage;
}

function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === "user";
  const isStreaming = message.id === "streaming";
  const actionButtons =
    !isUser && !isStreaming && "tool_results" in message && message.tool_results
      ? extractActionButtons(message as RalphMessage)
      : [];

  return (
    <div className={cn("flex gap-2.5", isUser && "flex-row-reverse")}>
      {/* Avatar */}
      <div
        className={cn(
          "flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-full",
          isUser
            ? "bg-neutral-200 dark:bg-neutral-700"
            : "bg-primary-100 dark:bg-primary-900/40",
        )}
      >
        {isUser ? (
          <User className="h-4 w-4 text-neutral-600 dark:text-neutral-300" />
        ) : (
          <Bot className="h-4 w-4 text-primary-600 dark:text-primary-400" />
        )}
      </div>

      {/* Content */}
      <div className={cn("max-w-[85%] space-y-2", isUser && "items-end flex flex-col")}>
        <div
          className={cn(
            "rounded-2xl px-3.5 py-2.5",
            isUser
              ? "rounded-tr-sm bg-primary-600 text-white"
              : "rounded-tl-sm bg-neutral-100 text-neutral-900 dark:bg-neutral-800 dark:text-neutral-100",
          )}
        >
          {isUser ? (
            <p className="text-sm">{message.content}</p>
          ) : (
            <AssistantContent content={message.content} isStreaming={isStreaming} />
          )}
        </div>

        {/* Action buttons */}
        {actionButtons.length > 0 && (
          <div className="flex flex-wrap gap-1.5">
            {actionButtons.map(({ label, href }) => (
              <a
                key={href}
                href={href}
                className="inline-flex items-center gap-1 rounded-lg border border-primary-200 bg-primary-50 px-2.5 py-1 text-xs font-medium text-primary-700 hover:bg-primary-100 dark:border-primary-800 dark:bg-primary-900/20 dark:text-primary-300 dark:hover:bg-primary-900/40"
              >
                {label}
                <ExternalLink className="h-3 w-3" />
              </a>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function AssistantContent({
  content,
  isStreaming,
}: {
  content: string;
  isStreaming: boolean;
}) {
  return (
    <div className="text-sm leading-relaxed">
      {content ? (
        <div className="prose prose-sm prose-neutral dark:prose-invert max-w-none [&>*:first-child]:mt-0 [&>*:last-child]:mb-0">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
        </div>
      ) : isStreaming ? (
        <Loader2 className="h-4 w-4 animate-spin text-neutral-400" />
      ) : null}
      {isStreaming && content && (
        <span className="ml-0.5 inline-block h-4 w-0.5 animate-pulse bg-neutral-400" />
      )}
    </div>
  );
}

function ToolCallIndicator({ name }: { name: string }) {
  const label = name
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());

  return (
    <div className="flex items-center gap-2 text-xs text-neutral-400 dark:text-neutral-500">
      <div className="flex h-6 w-6 items-center justify-center rounded-full bg-amber-100 dark:bg-amber-900/20">
        <Wrench className="h-3.5 w-3.5 text-amber-600 dark:text-amber-400" />
      </div>
      <span className="flex items-center gap-1.5">
        <Loader2 className="h-3 w-3 animate-spin" />
        {label}…
      </span>
    </div>
  );
}
