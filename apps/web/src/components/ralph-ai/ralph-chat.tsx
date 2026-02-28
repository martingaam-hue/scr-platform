"use client";

import React, { useCallback, useEffect, useRef, useState } from "react";
import { Bot, User, Loader2, Wrench } from "lucide-react";
import { cn } from "@scr/ui";
import {
  RalphMessage,
  useConversation,
  useStreamMessage,
} from "@/lib/ralph";
import { RalphInput } from "./ralph-input";
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

export function RalphChat({
  conversationId,
  initialMessage,
  onClearInitial,
}: RalphChatProps) {
  const { data: conversation, refetch } = useConversation(conversationId);
  const [streamingContent, setStreamingContent] = useState<string | null>(null);
  const [activeToolCalls, setActiveToolCalls] = useState<string[]>([]);
  const bottomRef = useRef<HTMLDivElement>(null);

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

  // Sync active tool calls from the stream
  useEffect(() => {
    setActiveToolCalls(streamToolCalls);
  }, [streamToolCalls]);

  // Auto-scroll to bottom
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [conversation?.messages, streamingContent, activeToolCalls]);

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
        <RalphSuggestions onSelect={(s) => sendMessage(s)} />
      )}

      {/* Input */}
      <RalphInput
        onSend={sendMessage}
        isStreaming={isStreaming}
        initialValue={initialMessage}
        onClearInitial={onClearInitial}
      />
    </div>
  );
}

interface MessageBubbleProps {
  message: RalphMessage | { id: string; role: "assistant"; content: string; created_at: string };
}

function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === "user";
  const isStreaming = message.id === "streaming";

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
      <div
        className={cn(
          "max-w-[85%] rounded-2xl px-3.5 py-2.5",
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
        <pre className="whitespace-pre-wrap font-sans">{content}</pre>
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
