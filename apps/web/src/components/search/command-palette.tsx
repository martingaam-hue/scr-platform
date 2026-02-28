"use client";

import React, { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { FileText, Layers, LayoutDashboard, Search, X } from "lucide-react";
import { cn } from "@scr/ui";
import { useSearch } from "@/lib/search";
import { useSearchStore } from "@/lib/store";

export function CommandPalette() {
  const { isOpen, close } = useSearchStore();
  const [query, setQuery] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);
  const router = useRouter();
  const { data, isFetching } = useSearch(query, isOpen);

  // Focus input when palette opens; clear query on close
  useEffect(() => {
    if (isOpen) {
      setTimeout(() => inputRef.current?.focus(), 50);
    } else {
      setQuery("");
    }
  }, [isOpen]);

  // Global keyboard shortcut ⌘K / Ctrl+K
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        useSearchStore.getState().toggle();
      }
      if (e.key === "Escape" && isOpen) {
        close();
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [isOpen, close]);

  if (!isOpen) return null;

  const hasResults =
    data &&
    (data.projects.length > 0 || data.listings.length > 0 || data.documents.length > 0);

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 z-50 bg-black/40 backdrop-blur-sm"
        onClick={close}
      />

      {/* Palette panel */}
      <div className="fixed left-1/2 top-[20vh] z-50 w-full max-w-xl -translate-x-1/2 overflow-hidden rounded-xl border border-neutral-200 bg-white shadow-2xl dark:border-neutral-700 dark:bg-neutral-900">

        {/* Search input */}
        <div className="flex items-center gap-3 border-b border-neutral-200 px-4 py-3 dark:border-neutral-700">
          <Search className="h-4 w-4 shrink-0 text-neutral-400" />
          <input
            ref={inputRef}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search projects, listings, documents..."
            className="flex-1 bg-transparent text-sm outline-none placeholder:text-neutral-400 dark:text-neutral-100"
          />
          {query && (
            <button
              onClick={() => setQuery("")}
              className="text-neutral-400 hover:text-neutral-600 dark:hover:text-neutral-300"
            >
              <X className="h-4 w-4" />
            </button>
          )}
          <kbd className="rounded border border-neutral-200 px-1.5 py-0.5 text-xs text-neutral-400 dark:border-neutral-700">
            Esc
          </kbd>
        </div>

        {/* Results */}
        <div className="max-h-96 overflow-y-auto">
          {isFetching && query.length >= 2 && (
            <p className="px-4 py-3 text-sm text-neutral-500">Searching…</p>
          )}

          {!isFetching && query.length >= 2 && !hasResults && (
            <p className="px-4 py-6 text-center text-sm text-neutral-500">
              No results for &ldquo;{query}&rdquo;
            </p>
          )}

          {data && data.projects.length > 0 && (
            <ResultSection label="Projects">
              {data.projects.map((hit) => (
                <ResultItem
                  key={hit.id}
                  icon={<LayoutDashboard className="h-4 w-4" />}
                  title={hit.name}
                  meta={[hit.project_type, hit.geography_country].filter(Boolean).join(" · ")}
                  onClick={() => {
                    router.push(`/projects/${hit.id}`);
                    close();
                  }}
                />
              ))}
            </ResultSection>
          )}

          {data && data.listings.length > 0 && (
            <ResultSection label="Marketplace">
              {data.listings.map((hit) => (
                <ResultItem
                  key={hit.id}
                  icon={<Layers className="h-4 w-4" />}
                  title={hit.headline}
                  meta={[hit.listing_type, hit.sector].filter(Boolean).join(" · ")}
                  onClick={() => {
                    router.push(`/marketplace/${hit.id}`);
                    close();
                  }}
                />
              ))}
            </ResultSection>
          )}

          {data && data.documents.length > 0 && (
            <ResultSection label="Documents">
              {data.documents.map((hit) => (
                <ResultItem
                  key={hit.id}
                  icon={<FileText className="h-4 w-4" />}
                  title={hit.filename}
                  meta={hit.snippet ?? hit.document_type ?? undefined}
                  onClick={() => {
                    router.push(`/data-room?document=${hit.id}`);
                    close();
                  }}
                />
              ))}
            </ResultSection>
          )}

          {!query && (
            <p className="px-4 py-6 text-center text-sm text-neutral-400">
              Type at least 2 characters to search
            </p>
          )}
        </div>
      </div>
    </>
  );
}

// ── Sub-components ────────────────────────────────────────────────────────────

function ResultSection({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <p className="px-4 py-2 text-xs font-semibold uppercase tracking-wider text-neutral-400">
        {label}
      </p>
      {children}
    </div>
  );
}

function ResultItem({
  icon,
  title,
  meta,
  onClick,
}: {
  icon: React.ReactNode;
  title: string;
  meta?: string;
  onClick: () => void;
}) {
  return (
    <button
      className="flex w-full items-center gap-3 px-4 py-2.5 text-left hover:bg-neutral-50 dark:hover:bg-neutral-800"
      onClick={onClick}
    >
      <span className="shrink-0 text-neutral-400">{icon}</span>
      <span className="min-w-0 flex-1">
        <span className="block truncate text-sm font-medium text-neutral-900 dark:text-neutral-100">
          {title}
        </span>
        {meta && (
          <span className="block truncate text-xs text-neutral-500">{meta}</span>
        )}
      </span>
    </button>
  );
}
