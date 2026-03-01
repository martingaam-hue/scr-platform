"use client";

import { useState } from "react";
import { cn } from "@scr/ui";
import { useCitations, type Citation } from "@/lib/citations";

// ── Types ──────────────────────────────────────────────────────────────────

interface CitationBadgesProps {
  aiTaskLogId: string | undefined;
  className?: string;
}

// ── Helpers ────────────────────────────────────────────────────────────────

function sourceTypeLabel(sourceType: string): string {
  switch (sourceType) {
    case "document":
      return "Document";
    case "web":
      return "Web";
    case "database":
      return "Database";
    case "user_input":
      return "User Input";
    default:
      return sourceType.replace(/_/g, " ");
  }
}

function confidenceLabel(confidence: number): string {
  return `${Math.round(confidence * 100)}%`;
}

// ── Inline badge (superscript number) ─────────────────────────────────────

function CitationBadge({
  index,
  citation,
  onClick,
  active,
}: {
  index: number;
  citation: Citation;
  onClick: () => void;
  active: boolean;
}) {
  const tooltip = [
    citation.document_name ?? sourceTypeLabel(citation.source_type),
    citation.page_or_section ? `p. ${citation.page_or_section}` : null,
    `Confidence: ${confidenceLabel(citation.confidence)}`,
  ]
    .filter(Boolean)
    .join(" · ");

  return (
    <button
      type="button"
      title={tooltip}
      onClick={onClick}
      className={cn(
        "inline-flex h-4 min-w-[1rem] items-center justify-center rounded-sm px-0.5 text-[10px] font-semibold leading-none transition-colors",
        active
          ? "bg-blue-600 text-white"
          : "bg-neutral-200 text-neutral-600 hover:bg-blue-100 hover:text-blue-700"
      )}
    >
      {index + 1}
    </button>
  );
}

// ── Expanded citation list ─────────────────────────────────────────────────

function CitationList({ citations }: { citations: Citation[] }) {
  return (
    <div className="mt-2 rounded-md border border-neutral-200 bg-white p-3 shadow-sm">
      <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-neutral-500">
        Sources
      </p>
      <ol className="space-y-1.5">
        {citations.map((c, i) => (
          <li key={c.id} className="flex items-start gap-2 text-xs">
            <span className="mt-0.5 flex h-4 min-w-[1rem] flex-shrink-0 items-center justify-center rounded-sm bg-neutral-200 px-0.5 text-[10px] font-semibold text-neutral-600">
              {i + 1}
            </span>
            <div className="min-w-0">
              <span className="font-medium text-neutral-800">
                {c.document_name ?? sourceTypeLabel(c.source_type)}
              </span>
              {c.page_or_section && (
                <span className="text-neutral-500">
                  {" "}
                  — {c.page_or_section}
                </span>
              )}
              <span className="ml-1 text-neutral-400">
                (confidence: {confidenceLabel(c.confidence)})
              </span>
              {c.verified === true && (
                <span className="ml-1 text-green-600">verified</span>
              )}
            </div>
          </li>
        ))}
      </ol>
    </div>
  );
}

// ── Main component ─────────────────────────────────────────────────────────

export function CitationBadges({ aiTaskLogId, className }: CitationBadgesProps) {
  const { data: citations, isLoading } = useCitations(aiTaskLogId);
  const [isExpanded, setIsExpanded] = useState(false);
  const [activeIndex, setActiveIndex] = useState<number | null>(null);

  if (!aiTaskLogId || isLoading || !citations || citations.length === 0) {
    return null;
  }

  function handleBadgeClick(index: number) {
    if (activeIndex === index && isExpanded) {
      setIsExpanded(false);
      setActiveIndex(null);
    } else {
      setActiveIndex(index);
      setIsExpanded(true);
    }
  }

  return (
    <span className={cn("inline-block", className)}>
      <span className="inline-flex items-center gap-0.5">
        {citations.map((c, i) => (
          <CitationBadge
            key={c.id}
            index={i}
            citation={c}
            onClick={() => handleBadgeClick(i)}
            active={isExpanded && activeIndex === i}
          />
        ))}
      </span>
      {isExpanded && <CitationList citations={citations} />}
    </span>
  );
}
