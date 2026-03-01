"use client";

import { useState } from "react";
import { BookOpen, Search, CheckCircle, XCircle, HelpCircle } from "lucide-react";
import {
  useCitationStats,
  useCitations,
  useVerifyCitation,
  type Citation,
} from "@/lib/citations";

// ── Helpers ────────────────────────────────────────────────────────────────

function confidenceBadge(confidence: number) {
  if (confidence >= 0.8) {
    return (
      <span className="rounded-full bg-green-100 px-2 py-0.5 text-xs font-medium text-green-700">
        High {(confidence * 100).toFixed(0)}%
      </span>
    );
  }
  if (confidence >= 0.5) {
    return (
      <span className="rounded-full bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-700">
        Medium {(confidence * 100).toFixed(0)}%
      </span>
    );
  }
  return (
    <span className="rounded-full bg-red-100 px-2 py-0.5 text-xs font-medium text-red-700">
      Low {(confidence * 100).toFixed(0)}%
    </span>
  );
}

function verifiedBadge(verified: boolean | null) {
  if (verified === true) {
    return (
      <span className="inline-flex items-center gap-1 text-xs text-green-600">
        <CheckCircle className="h-3 w-3" /> Verified
      </span>
    );
  }
  if (verified === false) {
    return (
      <span className="inline-flex items-center gap-1 text-xs text-red-500">
        <XCircle className="h-3 w-3" /> Incorrect
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 text-xs text-neutral-400">
      <HelpCircle className="h-3 w-3" /> Unverified
    </span>
  );
}

// ── Stat card ─────────────────────────────────────────────────────────────

function StatCard({ label, value, sub }: { label: string; value: string | number; sub?: string }) {
  return (
    <div className="rounded-lg border border-neutral-200 bg-white p-4">
      <p className="text-xs font-medium text-neutral-500">{label}</p>
      <p className="mt-1 text-2xl font-bold text-neutral-900">{value}</p>
      {sub && <p className="mt-0.5 text-xs text-neutral-400">{sub}</p>}
    </div>
  );
}

// ── Citation card ──────────────────────────────────────────────────────────

function CitationCard({ citation }: { citation: Citation }) {
  const verify = useVerifyCitation();

  return (
    <div className="rounded-lg border border-neutral-200 bg-white p-4 space-y-2 hover:border-neutral-300 transition-colors">
      <div className="flex items-start justify-between gap-4">
        <p className="text-sm text-neutral-800 italic line-clamp-3">
          &ldquo;{citation.claim_text}&rdquo;
        </p>
        <div className="shrink-0">{confidenceBadge(citation.confidence)}</div>
      </div>
      <div className="flex flex-wrap items-center gap-3 pt-1">
        {citation.document_name && (
          <span className="inline-flex items-center gap-1 text-xs text-neutral-500">
            <BookOpen className="h-3 w-3" />
            {citation.document_name}
            {citation.page_or_section && (
              <span className="text-neutral-400"> · {citation.page_or_section}</span>
            )}
          </span>
        )}
        <span className="rounded bg-neutral-100 px-1.5 py-0.5 text-xs text-neutral-600">
          {citation.source_type}
        </span>
        {verifiedBadge(citation.verified)}
      </div>
      {citation.verified === null && (
        <div className="flex gap-2 pt-1">
          <button
            onClick={() => verify.mutate({ citationId: citation.id, isCorrect: true })}
            disabled={verify.isPending}
            className="rounded px-2 py-1 text-xs font-medium text-green-700 border border-green-200 hover:bg-green-50 transition-colors disabled:opacity-50"
          >
            Mark Correct
          </button>
          <button
            onClick={() => verify.mutate({ citationId: citation.id, isCorrect: false })}
            disabled={verify.isPending}
            className="rounded px-2 py-1 text-xs font-medium text-red-600 border border-red-200 hover:bg-red-50 transition-colors disabled:opacity-50"
          >
            Mark Incorrect
          </button>
        </div>
      )}
    </div>
  );
}

// ── Page ───────────────────────────────────────────────────────────────────

type GroupBy = "analysis" | "document";

export default function CitationsPage() {
  const [search, setSearch] = useState("");
  const [groupBy, setGroupBy] = useState<GroupBy>("analysis");
  const [aiTaskLogId, setAiTaskLogId] = useState<string>("");

  const { data: stats, isLoading: statsLoading } = useCitationStats();
  const { data: citations, isLoading: citationsLoading } = useCitations(aiTaskLogId || undefined);

  const allCitations: Citation[] = citations ?? [];

  const filtered = allCitations.filter(
    (c) =>
      !search ||
      c.claim_text.toLowerCase().includes(search.toLowerCase()) ||
      (c.document_name ?? "").toLowerCase().includes(search.toLowerCase()) ||
      c.source_type.toLowerCase().includes(search.toLowerCase())
  );

  // Group citations
  const grouped: Record<string, Citation[]> = {};
  for (const c of filtered) {
    const key =
      groupBy === "document"
        ? c.document_name ?? "Unknown Document"
        : c.source_type;
    if (!grouped[key]) grouped[key] = [];
    grouped[key].push(c);
  }

  // Source type breakdown from stats
  const sourceBreakdown = stats?.by_source_type ?? {};

  return (
    <div className="p-8 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-indigo-100">
            <BookOpen className="h-5 w-5 text-indigo-600" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-neutral-900">AI Citations & Sources</h1>
            <p className="text-sm text-neutral-500">Review and verify AI-generated citation claims</p>
          </div>
        </div>

        {/* Group by toggle */}
        <div className="flex items-center gap-2">
          <span className="text-xs text-neutral-500">Group by:</span>
          <div className="flex rounded-lg border border-neutral-200 overflow-hidden">
            <button
              onClick={() => setGroupBy("analysis")}
              className={`px-3 py-1.5 text-xs font-medium transition-colors ${
                groupBy === "analysis" ? "bg-primary-600 text-white" : "bg-white text-neutral-600 hover:bg-neutral-50"
              }`}
            >
              Analysis Type
            </button>
            <button
              onClick={() => setGroupBy("document")}
              className={`px-3 py-1.5 text-xs font-medium transition-colors ${
                groupBy === "document" ? "bg-primary-600 text-white" : "bg-white text-neutral-600 hover:bg-neutral-50"
              }`}
            >
              Document
            </button>
          </div>
        </div>
      </div>

      {/* Stats */}
      {statsLoading ? (
        <div className="grid grid-cols-4 gap-4 animate-pulse">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="rounded-lg border border-neutral-200 bg-white p-4">
              <div className="h-3 w-20 bg-neutral-100 rounded mb-2" />
              <div className="h-7 w-16 bg-neutral-200 rounded" />
            </div>
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-4 gap-4">
          <StatCard label="Total Citations" value={stats?.total_citations ?? 0} />
          <StatCard label="Verified" value={stats?.verified_count ?? 0} />
          <StatCard label="Unverified" value={stats?.unverified_count ?? 0} />
          <StatCard
            label="Avg Confidence"
            value={stats?.avg_confidence != null ? `${(stats.avg_confidence * 100).toFixed(1)}%` : "—"}
          />
        </div>
      )}

      {/* Source type breakdown */}
      {Object.keys(sourceBreakdown).length > 0 && (
        <div className="flex flex-wrap gap-2">
          {Object.entries(sourceBreakdown).map(([type, count]) => (
            <span
              key={type}
              className="rounded-full border border-neutral-200 bg-white px-3 py-1 text-xs text-neutral-600"
            >
              {type}: <strong>{count}</strong>
            </span>
          ))}
        </div>
      )}

      {/* Search + AI Task Log ID input */}
      <div className="flex gap-3">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-neutral-400" />
          <input
            type="text"
            placeholder="Search citations…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full rounded-lg border border-neutral-200 py-2 pl-9 pr-3 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
          />
        </div>
        <input
          type="text"
          placeholder="AI Task Log ID (to load specific citations)"
          value={aiTaskLogId}
          onChange={(e) => setAiTaskLogId(e.target.value)}
          className="rounded-lg border border-neutral-200 px-3 py-2 text-sm w-72 focus:outline-none focus:ring-2 focus:ring-primary-500"
        />
      </div>

      {/* Citation cards */}
      {citationsLoading ? (
        <div className="space-y-3 animate-pulse">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="rounded-lg border border-neutral-200 bg-white p-4 space-y-2">
              <div className="h-4 bg-neutral-100 rounded w-3/4" />
              <div className="h-3 bg-neutral-100 rounded w-1/2" />
            </div>
          ))}
        </div>
      ) : !aiTaskLogId ? (
        <div className="rounded-lg border border-neutral-200 bg-white py-16 text-center text-neutral-400 text-sm">
          Enter an AI Task Log ID above to load citations, or view stats above for org-wide summary
        </div>
      ) : filtered.length === 0 ? (
        <div className="rounded-lg border border-neutral-200 bg-white py-16 text-center text-neutral-400 text-sm">
          No data available
        </div>
      ) : (
        <div className="space-y-6">
          {Object.entries(grouped).map(([group, items]) => (
            <div key={group}>
              <h3 className="mb-3 text-xs font-semibold uppercase tracking-widest text-neutral-400">
                {group} ({items.length})
              </h3>
              <div className="space-y-3">
                {items.map((c) => (
                  <CitationCard key={c.id} citation={c} />
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
