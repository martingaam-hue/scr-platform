"use client";

import React, { useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { Bookmark, Search, X, SlidersHorizontal, Loader2 } from "lucide-react";
import { Badge, Button, Card, CardContent, EmptyState } from "@scr/ui";
import { cn } from "@scr/ui";
import {
  useSavedSearches,
  useScreenerSearch,
  useSaveSearch,
  type ParsedFilters,
  type ScreenerResult,
  type ScreenerResponse,
  type SavedSearch,
} from "@/lib/screener";

// ── Signal score badge ────────────────────────────────────────────────────

function SignalBadge({ score }: { score: number | null }) {
  if (score === null) return <span className="text-xs text-neutral-400">—</span>;
  const color =
    score >= 75
      ? "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300"
      : score >= 50
        ? "bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-300"
        : "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300";
  return (
    <span className={cn("rounded-full px-2 py-0.5 text-xs font-semibold", color)}>
      {score}
    </span>
  );
}

// ── Filter pill ───────────────────────────────────────────────────────────

function FilterPill({
  label,
  onRemove,
}: {
  label: string;
  onRemove: () => void;
}) {
  return (
    <span className="flex items-center gap-1 rounded-full border border-primary-200 bg-primary-50 px-2.5 py-1 text-xs font-medium text-primary-700 dark:border-primary-800 dark:bg-primary-950/30 dark:text-primary-300">
      {label}
      <button onClick={onRemove} className="ml-0.5 rounded-full hover:text-primary-900">
        <X className="h-3 w-3" />
      </button>
    </span>
  );
}

// ── Result card ───────────────────────────────────────────────────────────

function ResultCard({
  result,
  onClick,
}: {
  result: ScreenerResult;
  onClick: () => void;
}) {
  const formatTicket = (val: number | null, currency: string | null) => {
    if (!val) return null;
    const m = val / 1_000_000;
    return `${currency ?? "EUR"} ${m >= 1000 ? `${(m / 1000).toFixed(1)}B` : `${m.toFixed(1)}M`}`;
  };

  return (
    <Card
      className="cursor-pointer transition-shadow hover:shadow-md"
      onClick={onClick}
    >
      <CardContent className="p-4">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0 flex-1">
            <p className="truncate font-semibold text-neutral-900 dark:text-neutral-100">
              {result.name}
            </p>
            <div className="mt-1 flex flex-wrap gap-1.5">
              {result.project_type && (
                <span className="rounded bg-neutral-100 px-1.5 py-0.5 text-xs text-neutral-600 dark:bg-neutral-800 dark:text-neutral-400 capitalize">
                  {result.project_type.replace(/_/g, " ")}
                </span>
              )}
              {result.geography_country && (
                <span className="text-xs text-neutral-500">
                  {result.geography_country}
                </span>
              )}
              {result.stage && (
                <span className="rounded bg-neutral-100 px-1.5 py-0.5 text-xs capitalize text-neutral-500 dark:bg-neutral-800">
                  {result.stage.replace(/_/g, " ")}
                </span>
              )}
            </div>
          </div>
          <div className="flex flex-col items-end gap-1 shrink-0">
            <SignalBadge score={result.signal_score} />
            {formatTicket(result.total_investment_required, result.currency) && (
              <span className="text-xs text-neutral-500">
                {formatTicket(result.total_investment_required, result.currency)}
              </span>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

// ── Save search modal ─────────────────────────────────────────────────────

function SaveSearchModal({
  query,
  filters,
  onClose,
}: {
  query: string;
  filters: ParsedFilters;
  onClose: () => void;
}) {
  const [name, setName] = useState(query.slice(0, 60));
  const [notify, setNotify] = useState(false);
  const saveSearch = useSaveSearch();

  function handleSave() {
    saveSearch.mutate(
      { name, query, filters, notify_new_matches: notify },
      { onSuccess: () => onClose() },
    );
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm">
      <div className="w-full max-w-md rounded-xl border border-neutral-200 bg-white p-6 shadow-xl dark:border-neutral-700 dark:bg-neutral-900">
        <h2 className="mb-4 text-lg font-semibold text-neutral-900 dark:text-neutral-100">
          Save this search
        </h2>
        <input
          className="mb-3 w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 dark:border-neutral-700 dark:bg-neutral-800 dark:text-neutral-100"
          placeholder="Search name..."
          value={name}
          onChange={(e) => setName(e.target.value)}
        />
        <label className="flex items-center gap-2 text-sm text-neutral-600 dark:text-neutral-300">
          <input
            type="checkbox"
            checked={notify}
            onChange={(e) => setNotify(e.target.checked)}
            className="rounded"
          />
          Notify me when new matching deals are added
        </label>
        <div className="mt-4 flex gap-2">
          <Button onClick={handleSave} disabled={saveSearch.isPending || !name.trim()}>
            {saveSearch.isPending ? "Saving..." : "Save"}
          </Button>
          <Button variant="outline" onClick={onClose}>
            Cancel
          </Button>
        </div>
      </div>
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────

export default function SmartScreenerPage() {
  const router = useRouter();
  const inputRef = useRef<HTMLInputElement>(null);

  const [query, setQuery] = useState("");
  const [response, setResponse] = useState<ScreenerResponse | null>(null);
  const [showSaveModal, setShowSaveModal] = useState(false);
  const [activeFilters, setActiveFilters] = useState<ParsedFilters>({});

  const { data: savedSearches = [] } = useSavedSearches();
  const searchMutation = useScreenerSearch();

  function handleSearch(searchQuery?: string) {
    const q = searchQuery ?? query;
    if (!q.trim()) return;
    searchMutation.mutate(
      { query: q, existingFilters: Object.keys(activeFilters).length ? activeFilters : undefined },
      {
        onSuccess: (data) => {
          setResponse(data);
          setActiveFilters(data.parsed_filters);
        },
      },
    );
  }

  function removeFilter(key: keyof ParsedFilters, value?: string) {
    setActiveFilters((prev) => {
      const next = { ...prev };
      if (Array.isArray(next[key]) && value) {
        (next[key] as string[]) = (next[key] as string[]).filter((v) => v !== value);
        if ((next[key] as string[]).length === 0) delete next[key];
      } else {
        delete next[key];
      }
      return next;
    });
  }

  // Build filter pills from activeFilters
  const filterPills: { label: string; onRemove: () => void }[] = [];
  if (activeFilters.project_types) {
    activeFilters.project_types.forEach((pt) =>
      filterPills.push({ label: pt, onRemove: () => removeFilter("project_types", pt) })
    );
  }
  if (activeFilters.geographies) {
    activeFilters.geographies.forEach((g) =>
      filterPills.push({ label: g, onRemove: () => removeFilter("geographies", g) })
    );
  }
  if (activeFilters.stages) {
    activeFilters.stages.forEach((s) =>
      filterPills.push({ label: s, onRemove: () => removeFilter("stages", s) })
    );
  }
  if (activeFilters.min_signal_score !== undefined) {
    filterPills.push({
      label: `Score >= ${activeFilters.min_signal_score}`,
      onRemove: () => removeFilter("min_signal_score"),
    });
  }
  if (activeFilters.min_ticket_size !== undefined) {
    filterPills.push({
      label: `>= EUR${activeFilters.min_ticket_size}M`,
      onRemove: () => removeFilter("min_ticket_size"),
    });
  }

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-neutral-900 dark:text-neutral-100">
          Smart Screener
        </h1>
        <p className="mt-1 text-sm text-neutral-500">
          Search deals using natural language
        </p>
      </div>

      {/* Search bar */}
      <div className="relative">
        <div className="flex items-center gap-2 rounded-xl border border-neutral-200 bg-white px-4 py-3 shadow-sm focus-within:border-primary-400 focus-within:ring-2 focus-within:ring-primary-100 dark:border-neutral-700 dark:bg-neutral-900">
          <Search className="h-5 w-5 shrink-0 text-neutral-400" />
          <input
            ref={inputRef}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSearch()}
            placeholder="e.g. solar projects in Spain above 50MW"
            className="flex-1 bg-transparent text-sm text-neutral-900 outline-none placeholder:text-neutral-400 dark:text-neutral-100"
          />
          {query && (
            <button onClick={() => setQuery("")} className="text-neutral-400 hover:text-neutral-600">
              <X className="h-4 w-4" />
            </button>
          )}
          <Button onClick={() => handleSearch()} disabled={searchMutation.isPending || !query.trim()}>
            {searchMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : "Search"}
          </Button>
        </div>
      </div>

      {/* Filter pills */}
      {filterPills.length > 0 && (
        <div className="flex flex-wrap gap-2">
          <span className="flex items-center gap-1 text-xs text-neutral-500">
            <SlidersHorizontal className="h-3.5 w-3.5" />
            Filters:
          </span>
          {filterPills.map((pill, i) => (
            <FilterPill key={i} label={pill.label} onRemove={pill.onRemove} />
          ))}
          <button
            onClick={() => setActiveFilters({})}
            className="text-xs text-neutral-400 hover:text-neutral-600"
          >
            Clear all
          </button>
        </div>
      )}

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[1fr_240px]">
        {/* Results */}
        <div className="space-y-4">
          {response && (
            <>
              <div className="flex items-center justify-between">
                <p className="text-sm text-neutral-500">
                  {response.total_results} result{response.total_results !== 1 ? "s" : ""}
                </p>
                {response.total_results > 0 && (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setShowSaveModal(true)}
                  >
                    <Bookmark className="mr-1.5 h-3.5 w-3.5" />
                    Save search
                  </Button>
                )}
              </div>

              {/* Suggestions */}
              {response.suggestions.length > 0 && (
                <div className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800 dark:border-amber-800/30 dark:bg-amber-950/20 dark:text-amber-300">
                  <p className="font-medium mb-1">Suggestions:</p>
                  <ul className="list-disc list-inside space-y-0.5">
                    {response.suggestions.map((s, i) => (
                      <li key={i}>{s}</li>
                    ))}
                  </ul>
                </div>
              )}

              {response.results.length === 0 ? (
                <EmptyState
                  title="No deals found"
                  description="Try adjusting your search query or removing some filters."
                />
              ) : (
                <div className="grid gap-3">
                  {response.results.map((r) => (
                    <ResultCard
                      key={r.id}
                      result={r}
                      onClick={() => router.push(`/projects/${r.id}`)}
                    />
                  ))}
                </div>
              )}
            </>
          )}

          {!response && !searchMutation.isPending && (
            <div className="rounded-xl border border-dashed border-neutral-200 py-16 text-center dark:border-neutral-700">
              <Search className="mx-auto mb-3 h-8 w-8 text-neutral-300" />
              <p className="text-sm text-neutral-500">
                Type a natural language query to find deals
              </p>
              <p className="mt-1 text-xs text-neutral-400">
                Try: &ldquo;high quality wind farms in Northern Europe&rdquo;
              </p>
            </div>
          )}
        </div>

        {/* Saved searches sidebar */}
        <div className="space-y-3">
          <p className="text-xs font-semibold uppercase tracking-wider text-neutral-400">
            Saved Searches
          </p>
          {savedSearches.length === 0 ? (
            <p className="text-xs text-neutral-400">No saved searches yet.</p>
          ) : (
            savedSearches.map((s) => (
              <button
                key={s.id}
                className="w-full rounded-lg border border-neutral-200 bg-white p-3 text-left hover:border-primary-300 dark:border-neutral-700 dark:bg-neutral-900"
                onClick={() => {
                  setQuery(s.query);
                  handleSearch(s.query);
                }}
              >
                <p className="truncate text-sm font-medium text-neutral-800 dark:text-neutral-200">
                  {s.name}
                </p>
                <p className="mt-0.5 truncate text-xs text-neutral-400">{s.query}</p>
                {s.notify_new_matches && (
                  <span className="mt-1 inline-block rounded-full bg-primary-50 px-1.5 py-0.5 text-xs text-primary-600 dark:bg-primary-950/30 dark:text-primary-400">
                    Notifications on
                  </span>
                )}
              </button>
            ))
          )}
        </div>
      </div>

      {/* Save modal */}
      {showSaveModal && response && (
        <SaveSearchModal
          query={response.query}
          filters={response.parsed_filters}
          onClose={() => setShowSaveModal(false)}
        />
      )}
    </div>
  );
}
