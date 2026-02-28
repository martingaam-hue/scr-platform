"use client";

import React, { useState } from "react";
import { Bot, Plus, Trash2, X, MessageSquare } from "lucide-react";
import { cn } from "@scr/ui";
import {
  useConversations,
  useCreateConversation,
  useDeleteConversation,
  type RalphConversation,
} from "@/lib/ralph";
import { useRalphStore } from "@/lib/store";
import { RalphChat } from "./ralph-chat";

export function RalphPanel() {
  const { isOpen, close, activeConversationId, setActiveConversationId } =
    useRalphStore();
  const [pendingMessage, setPendingMessage] = useState<string | undefined>();

  const { data: conversations = [], isLoading } = useConversations();
  const createConversation = useCreateConversation();
  const deleteConversation = useDeleteConversation();

  const handleNewConversation = async () => {
    const conv = await createConversation.mutateAsync({ title: "New conversation" });
    setActiveConversationId(conv.id);
  };

  const handleDelete = async (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    await deleteConversation.mutateAsync(id);
    if (activeConversationId === id) {
      setActiveConversationId(null);
    }
  };

  if (!isOpen) return null;

  return (
    <>
      {/* Backdrop (mobile only) */}
      <div
        className="fixed inset-0 z-30 bg-black/20 backdrop-blur-sm md:hidden"
        onClick={close}
      />

      {/* Panel */}
      <aside className="fixed bottom-0 right-0 top-[var(--topbar-height)] z-30 flex w-[400px] flex-col border-l border-neutral-200 bg-white shadow-xl dark:border-neutral-800 dark:bg-neutral-900">
        {/* Header */}
        <div className="flex items-center gap-3 border-b border-neutral-200 px-4 py-3 dark:border-neutral-800">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary-100 dark:bg-primary-900/30">
            <Bot className="h-4.5 w-4.5 text-primary-600 dark:text-primary-400" />
          </div>
          <div className="flex-1">
            <h2 className="text-sm font-semibold text-neutral-900 dark:text-neutral-100">
              Ralph AI
            </h2>
            <p className="text-[10px] text-neutral-400 dark:text-neutral-500">
              Your investment analyst
            </p>
          </div>
          <div className="flex items-center gap-1">
            {activeConversationId && (
              <button
                onClick={handleNewConversation}
                className="rounded-md p-1.5 text-neutral-400 hover:bg-neutral-100 hover:text-neutral-700 dark:hover:bg-neutral-800 dark:hover:text-neutral-200"
                title="New conversation"
              >
                <Plus className="h-4 w-4" />
              </button>
            )}
            <button
              onClick={close}
              className="rounded-md p-1.5 text-neutral-400 hover:bg-neutral-100 hover:text-neutral-700 dark:hover:bg-neutral-800 dark:hover:text-neutral-200"
              title="Close"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        </div>

        {/* Body */}
        {activeConversationId ? (
          <div className="flex flex-1 flex-col overflow-hidden">
            {/* Back to list */}
            <button
              onClick={() => setActiveConversationId(null)}
              className="flex items-center gap-2 border-b border-neutral-100 px-4 py-2 text-xs text-neutral-500 hover:bg-neutral-50 dark:border-neutral-800 dark:text-neutral-400 dark:hover:bg-neutral-800/50"
            >
              ← All conversations
            </button>
            <div className="flex-1 overflow-hidden">
              <RalphChat
                conversationId={activeConversationId}
                initialMessage={pendingMessage}
                onClearInitial={() => setPendingMessage(undefined)}
              />
            </div>
          </div>
        ) : (
          <ConversationList
            conversations={conversations}
            isLoading={isLoading}
            onSelect={setActiveConversationId}
            onDelete={handleDelete}
            onNew={handleNewConversation}
            isCreating={createConversation.isPending}
          />
        )}
      </aside>
    </>
  );
}

interface ConversationListProps {
  conversations: RalphConversation[];
  isLoading: boolean;
  onSelect: (id: string) => void;
  onDelete: (e: React.MouseEvent, id: string) => void;
  onNew: () => void;
  isCreating: boolean;
}

function ConversationList({
  conversations,
  isLoading,
  onSelect,
  onDelete,
  onNew,
  isCreating,
}: ConversationListProps) {
  return (
    <div className="flex flex-1 flex-col overflow-hidden">
      {/* New conversation CTA */}
      <div className="p-4">
        <button
          onClick={onNew}
          disabled={isCreating}
          className="flex w-full items-center justify-center gap-2 rounded-xl border-2 border-dashed border-neutral-200 py-3 text-sm text-neutral-500 transition-colors hover:border-primary-300 hover:text-primary-600 dark:border-neutral-700 dark:text-neutral-400 dark:hover:border-primary-600 dark:hover:text-primary-400"
        >
          <Plus className="h-4 w-4" />
          New conversation
        </button>
      </div>

      {/* List */}
      <div className="flex-1 overflow-y-auto px-4 pb-4">
        {isLoading ? (
          <div className="space-y-2">
            {[1, 2, 3].map((n) => (
              <div
                key={n}
                className="h-14 animate-pulse rounded-xl bg-neutral-100 dark:bg-neutral-800"
              />
            ))}
          </div>
        ) : conversations.length === 0 ? (
          <div className="flex flex-col items-center justify-center gap-3 py-12 text-center">
            <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-neutral-100 dark:bg-neutral-800">
              <MessageSquare className="h-6 w-6 text-neutral-400" />
            </div>
            <div>
              <p className="text-sm font-medium text-neutral-700 dark:text-neutral-300">
                No conversations yet
              </p>
              <p className="mt-0.5 text-xs text-neutral-400 dark:text-neutral-500">
                Start a new conversation to get insights
              </p>
            </div>
          </div>
        ) : (
          <div className="space-y-1.5">
            {conversations.map((conv) => (
              <ConversationItem
                key={conv.id}
                conversation={conv}
                onSelect={onSelect}
                onDelete={onDelete}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function ConversationItem({
  conversation,
  onSelect,
  onDelete,
}: {
  conversation: RalphConversation;
  onSelect: (id: string) => void;
  onDelete: (e: React.MouseEvent, id: string) => void;
}) {
  const updatedAt = new Date(conversation.updated_at);
  const timeLabel = formatRelativeTime(updatedAt);

  return (
    <button
      onClick={() => onSelect(conversation.id)}
      className="group flex w-full items-start gap-3 rounded-xl px-3 py-2.5 text-left transition-colors hover:bg-neutral-50 dark:hover:bg-neutral-800"
    >
      <div className="mt-0.5 flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-lg bg-primary-50 dark:bg-primary-900/20">
        <Bot className="h-4 w-4 text-primary-600 dark:text-primary-400" />
      </div>
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-medium text-neutral-800 dark:text-neutral-200">
          {conversation.title}
        </p>
        <p className="text-xs text-neutral-400 dark:text-neutral-500">
          {timeLabel}
        </p>
      </div>
      <button
        onClick={(e) => onDelete(e, conversation.id)}
        className="flex-shrink-0 rounded p-1 text-neutral-300 opacity-0 transition-opacity group-hover:opacity-100 hover:text-red-500 dark:text-neutral-600 dark:hover:text-red-400"
        title="Delete"
      >
        <Trash2 className="h-3.5 w-3.5" />
      </button>
    </button>
  );
}

function formatRelativeTime(date: Date): string {
  const now = new Date();
  const diff = now.getTime() - date.getTime();
  const minutes = Math.floor(diff / 60_000);
  const hours = Math.floor(diff / 3_600_000);
  const days = Math.floor(diff / 86_400_000);

  if (minutes < 1) return "Just now";
  if (minutes < 60) return `${minutes}m ago`;
  if (hours < 24) return `${hours}h ago`;
  if (days < 7) return `${days}d ago`;
  return date.toLocaleDateString();
}
