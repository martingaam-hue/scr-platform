"use client";

import { useState, useMemo, useRef, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  ArrowLeft,
  ArrowRight,
  Building2,
  Check,
  ChevronDown,
  ChevronUp,
  Globe,
  MapPin,
  MoreHorizontal,
  RefreshCw,
  TrendingUp,
  Users,
} from "lucide-react";
import { Badge, Card, CardContent, EmptyState, cn } from "@scr/ui";
import {
  useAllyRecommendations,
  useUpdateMatchStatus,
  alignmentColor,
  alignmentBarColor,
  statusLabel,
  statusVariant,
  ALIGNMENT_DIMENSIONS,
  PIPELINE_STAGES,
  type MatchingInvestor,
} from "@/lib/matching";
import { useProject } from "@/lib/projects";
import { AIFeedback } from "@/components/ai-feedback";

// ── Helpers ───────────────────────────────────────────────────────────────────

function fmtMoney(n: number): string {
  if (n >= 1_000_000) return `$${(n / 1_000_000).toFixed(0)}M`;
  if (n >= 1_000) return `$${(n / 1_000).toFixed(0)}K`;
  return `$${n}`;
}

function relativeDate(dateStr: string): string {
  const diff = Math.floor((Date.now() - new Date(dateStr).getTime()) / 86_400_000);
  if (diff === 0) return "Today";
  if (diff === 1) return "Yesterday";
  if (diff < 7) return `${diff} days ago`;
  if (diff < 30) return `${Math.floor(diff / 7)}w ago`;
  return new Date(dateStr).toLocaleDateString("en-GB", { day: "numeric", month: "short" });
}

function nameInitials(name: string): string {
  return name
    .split(/\s+/)
    .slice(0, 2)
    .map((w) => w[0] ?? "")
    .join("")
    .toUpperCase();
}

function matchScoreColor(score: number) {
  if (score >= 80) return { text: "text-green-600", dot: "bg-green-500", ring: "ring-green-100" };
  if (score >= 60) return { text: "text-amber-600", dot: "bg-amber-400", ring: "ring-amber-100" };
  return { text: "text-red-500", dot: "bg-red-400", ring: "ring-red-100" };
}

function primaryCTA(status: string): { label: string; nextStatus: string } | null {
  if (status === "suggested" || status === "viewed")
    return { label: "Express Interest", nextStatus: "interested" };
  if (status === "interested")
    return { label: "Request Introduction", nextStatus: "intro_requested" };
  if (status === "intro_requested")
    return { label: "Send Message", nextStatus: "engaged" };
  return null;
}

// ── Status three-dot menu ─────────────────────────────────────────────────────

function StatusMenu({ investor }: { investor: MatchingInvestor }) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const updateStatus = useUpdateMatchStatus();

  useEffect(() => {
    function onClickOutside(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", onClickOutside);
    return () => document.removeEventListener("mousedown", onClickOutside);
  }, []);

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen((v) => !v)}
        className="rounded-md p-1.5 text-neutral-400 hover:bg-neutral-100 hover:text-neutral-600"
        title="Update status"
      >
        <MoreHorizontal className="h-4 w-4" />
      </button>
      {open && (
        <div className="absolute right-0 top-full z-20 mt-1 min-w-[180px] overflow-hidden rounded-xl border border-neutral-200 bg-white shadow-lg">
          <p className="px-3 py-2 text-[10px] font-semibold uppercase tracking-wider text-neutral-400">
            Update Status
          </p>
          {PIPELINE_STAGES.map((stage) => (
            <button
              key={stage.value}
              disabled={!investor.match_id || updateStatus.isPending}
              onClick={() => {
                if (!investor.match_id) return;
                updateStatus.mutate({ matchId: investor.match_id, status: stage.value });
                setOpen(false);
              }}
              className={cn(
                "flex w-full items-center gap-2.5 px-3 py-2.5 text-sm transition-colors hover:bg-neutral-50",
                investor.status === stage.value
                  ? "font-semibold text-[#1B2A4A]"
                  : "text-neutral-700"
              )}
            >
              <span className="flex h-4 w-4 items-center justify-center">
                {investor.status === stage.value && (
                  <Check className="h-3.5 w-3.5 text-[#1B2A4A]" />
                )}
              </span>
              {stage.label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Alignment breakdown (collapsible) ────────────────────────────────────────

function AlignmentBreakdown({ alignment }: { alignment: MatchingInvestor["alignment"] }) {
  return (
    <div className="space-y-2.5">
      {ALIGNMENT_DIMENSIONS.map((dim) => {
        const score = alignment[dim.key] as number;
        const pct = Math.round((score / dim.max) * 100);
        return (
          <div key={dim.key}>
            <div className="mb-0.5 flex justify-between text-xs">
              <span className="text-neutral-500">{dim.label}</span>
              <span className={cn("font-semibold", alignmentColor(pct))}>
                {score}/{dim.max}
              </span>
            </div>
            <div className="h-1.5 overflow-hidden rounded-full bg-neutral-100">
              <div
                className={cn("h-full rounded-full transition-all", alignmentBarColor(pct))}
                style={{ width: `${pct}%` }}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
}

// ── Investor card ─────────────────────────────────────────────────────────────

function InvestorCard({ investor, projectId: _projectId }: { investor: MatchingInvestor; projectId: string }) {
  const router = useRouter();
  const updateStatus = useUpdateMatchStatus();
  const [showAlignment, setShowAlignment] = useState(false);

  const { text, dot, ring } = matchScoreColor(investor.alignment.overall);
  const cta = primaryCTA(investor.status);

  const ticketMin = Number(investor.ticket_size_min);
  const ticketMax = Number(investor.ticket_size_max);
  const ticketLabel =
    ticketMin || ticketMax
      ? `${fmtMoney(ticketMin)} – ${fmtMoney(ticketMax)}`
      : "—";

  const focusLabel =
    investor.sectors.length > 0
      ? investor.sectors
          .slice(0, 3)
          .map((s) => s.replace(/_/g, " "))
          .join(", ") + (investor.sectors.length > 3 ? ` +${investor.sectors.length - 3}` : "")
      : "All sectors";

  const locationLabel =
    investor.geographies.length > 0
      ? investor.geographies.slice(0, 2).join(", ") +
        (investor.geographies.length > 2 ? ` +${investor.geographies.length - 2}` : "")
      : "Global";

  // Chips: first 3 sectors + mandate stage chips if available (use risk tolerance as extra tag)
  const chips: string[] = [
    ...investor.sectors.slice(0, 3).map((s) => s.replace(/_/g, " ")),
    investor.risk_tolerance
      ? investor.risk_tolerance.charAt(0).toUpperCase() + investor.risk_tolerance.slice(1) + " Risk"
      : "",
  ].filter(Boolean);

  return (
    <div className="group rounded-xl border border-neutral-200 bg-white shadow-sm transition-shadow hover:shadow-md">
      <div className="p-5">
        {/* ── Top row: logo + name + match score ── */}
        <div className="flex items-start justify-between gap-4">
          <div className="flex items-center gap-3 min-w-0">
            {investor.logo_url ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={investor.logo_url}
                alt={investor.investor_name}
                className="h-12 w-12 rounded-xl border border-neutral-200 bg-white object-contain p-1"
              />
            ) : (
              <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-[#1B2A4A]/8 text-sm font-bold text-[#1B2A4A]">
                {nameInitials(investor.investor_name)}
              </div>
            )}
            <div className="min-w-0">
              <h3 className="truncate font-semibold text-neutral-900">
                {investor.investor_name}
              </h3>
              <p className="truncate text-sm text-neutral-500">
                {investor.mandate_name ?? "Investment Fund"}
              </p>
            </div>
          </div>

          <div className="flex shrink-0 items-start gap-2">
            {/* Match score */}
            <div className="flex flex-col items-end gap-1.5">
              <div className={cn("flex items-center gap-1.5 rounded-full px-2.5 py-1 ring-1", ring)}>
                <span className={cn("h-2 w-2 rounded-full", dot)} />
                <span className={cn("text-sm font-bold tabular-nums", text)}>
                  {investor.alignment.overall}%
                </span>
                <span className="text-xs text-neutral-400">match</span>
              </div>
              <Badge variant={statusVariant(investor.status)} className="text-xs">
                {statusLabel(investor.status)}
              </Badge>
            </div>
            {/* Three-dot menu */}
            <StatusMenu investor={investor} />
          </div>
        </div>

        {/* ── Info row: focus + ticket ── */}
        <div className="mt-4 grid grid-cols-2 gap-3">
          <div className="rounded-lg bg-neutral-50 px-3 py-2">
            <p className="text-[10px] font-medium uppercase tracking-wider text-neutral-400">
              Investment Focus
            </p>
            <p className="mt-0.5 truncate text-sm font-medium text-neutral-800">{focusLabel}</p>
          </div>
          <div className="rounded-lg bg-neutral-50 px-3 py-2">
            <p className="text-[10px] font-medium uppercase tracking-wider text-neutral-400">
              Ticket Size
            </p>
            <p className="mt-0.5 text-sm font-medium text-neutral-800">{ticketLabel}</p>
          </div>
        </div>

        {/* ── Location ── */}
        <div className="mt-3 flex items-center gap-1.5 text-sm text-neutral-500">
          <MapPin className="h-3.5 w-3.5 shrink-0 text-neutral-400" />
          <span>{locationLabel}</span>
        </div>

        {/* ── Chips ── */}
        {chips.length > 0 && (
          <div className="mt-3 flex flex-wrap gap-1.5">
            {chips.map((chip) => (
              <span
                key={chip}
                className="inline-flex items-center rounded-full border border-neutral-200 bg-white px-2.5 py-0.5 text-xs text-neutral-600"
              >
                {chip}
              </span>
            ))}
          </div>
        )}

        {/* ── Alignment detail toggle ── */}
        <button
          onClick={() => setShowAlignment((v) => !v)}
          className="mt-4 flex items-center gap-1 text-xs font-medium text-neutral-400 hover:text-neutral-700"
        >
          {showAlignment ? (
            <ChevronUp className="h-3.5 w-3.5" />
          ) : (
            <ChevronDown className="h-3.5 w-3.5" />
          )}
          {showAlignment ? "Hide" : "See"} alignment breakdown
        </button>

        {showAlignment && (
          <div className="mt-3 rounded-lg border border-neutral-100 bg-neutral-50 p-4">
            <div className="mb-3 flex items-center justify-between">
              <p className="text-xs font-semibold text-neutral-700">Alignment Breakdown</p>
              <span
                className={cn(
                  "text-sm font-bold tabular-nums",
                  alignmentColor(investor.alignment.overall)
                )}
              >
                {investor.alignment.overall}% overall
              </span>
            </div>
            <AlignmentBreakdown alignment={investor.alignment} />
          </div>
        )}
      </div>

      {/* ── Footer: CTAs ── */}
      <div className="flex items-center gap-3 border-t border-neutral-100 px-5 py-3">
        {cta ? (
          <button
            disabled={!investor.match_id || updateStatus.isPending}
            onClick={() => {
              if (!investor.match_id) return;
              updateStatus.mutate({
                matchId: investor.match_id,
                status: cta.nextStatus,
              });
            }}
            className="flex-1 rounded-lg bg-[#1B2A4A] py-2 text-sm font-medium text-white transition-colors hover:bg-[#243660] disabled:opacity-50"
          >
            {cta.label}
          </button>
        ) : (
          <div className="flex-1" />
        )}
        <button
          onClick={() => router.push(`/investors/${investor.investor_org_id}`)}
          className="flex items-center gap-1 text-sm font-medium text-neutral-500 transition-colors hover:text-[#1B2A4A]"
        >
          View Profile
          <ArrowRight className="h-3.5 w-3.5" />
        </button>
      </div>
    </div>
  );
}

// ── Activity timeline ─────────────────────────────────────────────────────────

function ActivityTimeline({ investors }: { investors: MatchingInvestor[] }) {
  const events = useMemo(
    () =>
      investors
        .filter((inv) => inv.match_id && inv.updated_at)
        .map((inv) => ({
          id: inv.match_id!,
          investor: inv.investor_name,
          status: inv.status,
          date: inv.updated_at!,
        }))
        .sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime())
        .slice(0, 20),
    [investors]
  );

  if (events.length === 0) {
    return (
      <EmptyState
        icon={<TrendingUp className="h-8 w-8" />}
        title="No activity yet"
        description="Match activity will appear here as investors engage with your project."
      />
    );
  }

  return (
    <div className="relative pl-8">
      {/* Vertical line */}
      <div className="absolute left-3 top-1 bottom-1 w-0.5 bg-neutral-100" />

      <div className="space-y-5">
        {events.map((ev) => {
          const variant = statusVariant(ev.status);
          const dotColor =
            variant === "success"
              ? "bg-green-500 ring-green-100"
              : variant === "info"
                ? "bg-blue-500 ring-blue-100"
                : variant === "warning"
                  ? "bg-amber-400 ring-amber-100"
                  : variant === "error"
                    ? "bg-red-400 ring-red-100"
                    : "bg-neutral-300 ring-neutral-100";

          return (
            <div key={ev.id} className="relative flex items-start gap-3">
              {/* Dot */}
              <div
                className={cn(
                  "absolute -left-8 mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full ring-2 text-[9px] font-bold text-white",
                  dotColor
                )}
              >
                {nameInitials(ev.investor)}
              </div>

              <div className="min-w-0 flex-1">
                <p className="text-sm font-medium text-neutral-800 leading-snug">
                  {ev.investor}
                </p>
                <p className="mt-0.5 flex items-center gap-1.5 text-xs text-neutral-500">
                  Moved to
                  <Badge variant={statusVariant(ev.status)} className="text-[10px]">
                    {statusLabel(ev.status)}
                  </Badge>
                </p>
              </div>

              <time className="shrink-0 text-xs text-neutral-400">
                {relativeDate(ev.date)}
              </time>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ── Filter types ──────────────────────────────────────────────────────────────

type FilterKey = "all" | "high_match" | "interested" | "engaged";
type SortKey = "best_match" | "most_recent";

const FILTERS: { key: FilterKey; label: string }[] = [
  { key: "all", label: "All" },
  { key: "high_match", label: "High Match ≥80%" },
  { key: "interested", label: "Interested" },
  { key: "engaged", label: "Engaged" },
];

// ── Page ──────────────────────────────────────────────────────────────────────

export default function ProjectMatchingPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [filter, setFilter] = useState<FilterKey>("all");
  const [sort, setSort] = useState<SortKey>("best_match");

  const { data: project } = useProject(id);
  const { data, isLoading } = useAllyRecommendations(id);

  // ── Derived stats ──────────────────────────────────────────────────────────
  const stats = useMemo(() => {
    if (!data) return null;
    const interested = data.items.filter((i) =>
      ["interested", "intro_requested", "engaged"].includes(i.status)
    ).length;
    const avgAlignment =
      data.items.length > 0
        ? Math.round(data.items.reduce((s, i) => s + i.alignment.overall, 0) / data.items.length)
        : 0;
    const activeMandates = new Set(data.items.map((i) => i.mandate_id).filter(Boolean)).size;
    return { total: data.total, interested, avgAlignment, activeMandates };
  }, [data]);

  // ── Filtered + sorted list ─────────────────────────────────────────────────
  const filteredItems = useMemo(() => {
    if (!data) return [];
    let items = [...data.items];

    switch (filter) {
      case "high_match":
        items = items.filter((i) => i.alignment.overall >= 80);
        break;
      case "interested":
        items = items.filter((i) =>
          ["interested", "intro_requested"].includes(i.status)
        );
        break;
      case "engaged":
        items = items.filter((i) => i.status === "engaged");
        break;
    }

    if (sort === "best_match") {
      items.sort((a, b) => b.alignment.overall - a.alignment.overall);
    } else {
      items.sort((a, b) => {
        const aTime = a.updated_at ? new Date(a.updated_at).getTime() : 0;
        const bTime = b.updated_at ? new Date(b.updated_at).getTime() : 0;
        return bTime - aTime;
      });
    }

    return items;
  }, [data, filter, sort]);

  return (
    <div className="mx-auto max-w-screen-xl p-6">

      {/* ── Page header ─────────────────────────────────────────────────── */}
      <div className="mb-6 flex items-start justify-between gap-4">
        <div>
          <button
            onClick={() => router.push(`/projects/${id}`)}
            className="mb-2 flex items-center gap-1.5 text-sm text-neutral-400 transition-colors hover:text-neutral-700"
          >
            <ArrowLeft className="h-4 w-4" />
            Back to project
          </button>
          <h1 className="text-2xl font-bold text-neutral-900">Investor Matching</h1>
          {project && (
            <p className="mt-1 text-sm text-neutral-500">
              Investors matched to{" "}
              <span className="font-medium text-neutral-700">{project.name}</span>
            </p>
          )}
        </div>
        <div className="flex shrink-0 items-center gap-3 pt-1">
          <AIFeedback
            taskType="matching"
            entityType="project"
            entityId={id}
            compact
          />
          <button
            onClick={() => router.push(`/projects/${id}/signal-score`)}
            className="flex items-center gap-1.5 rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm font-medium text-neutral-700 transition-colors hover:border-neutral-300 hover:bg-neutral-50"
          >
            <RefreshCw className="h-3.5 w-3.5" />
            Run Matching
          </button>
        </div>
      </div>

      {/* ── Stats strip ─────────────────────────────────────────────────── */}
      {stats && (
        <div className="mb-6 grid grid-cols-2 divide-x divide-neutral-100 overflow-hidden rounded-xl border border-neutral-200 bg-white shadow-sm sm:grid-cols-4">
          {[
            { label: "Total Matches", value: stats.total, icon: Users },
            {
              label: "Interested",
              value: stats.interested,
              icon: TrendingUp,
              color: "text-green-600",
            },
            { label: "Avg. Alignment", value: `${stats.avgAlignment}%`, icon: null },
            { label: "Active Mandates", value: stats.activeMandates, icon: Building2 },
          ].map(({ label, value, icon: Icon, color }) => (
            <div key={label} className="flex items-center gap-3 px-5 py-4">
              {Icon && (
                <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-neutral-50">
                  <Icon className="h-4 w-4 text-neutral-400" />
                </div>
              )}
              <div>
                <p className="text-xs text-neutral-500">{label}</p>
                <p className={cn("text-xl font-bold text-neutral-900", color)}>{value}</p>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* ── Main 2-col layout ───────────────────────────────────────────── */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">

        {/* Left — investor list (2/3) */}
        <div className="lg:col-span-2">

          {/* Filter + sort bar */}
          <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-1 rounded-lg border border-neutral-200 bg-white p-1">
              {FILTERS.map((f) => (
                <button
                  key={f.key}
                  onClick={() => setFilter(f.key)}
                  className={cn(
                    "rounded-md px-3 py-1.5 text-xs font-medium transition-colors",
                    filter === f.key
                      ? "bg-[#1B2A4A] text-white"
                      : "text-neutral-500 hover:bg-neutral-50 hover:text-neutral-800"
                  )}
                >
                  {f.label}
                </button>
              ))}
            </div>

            <div className="flex items-center gap-2">
              <span className="text-xs text-neutral-400">Sort:</span>
              <select
                value={sort}
                onChange={(e) => setSort(e.target.value as SortKey)}
                className="rounded-lg border border-neutral-200 bg-white px-3 py-1.5 text-xs text-neutral-700 focus:outline-none"
              >
                <option value="best_match">Best Match</option>
                <option value="most_recent">Most Recent</option>
              </select>
            </div>
          </div>

          {/* Cards */}
          {isLoading ? (
            <div className="space-y-4">
              {[1, 2, 3].map((i) => (
                <div key={i} className="h-64 animate-pulse rounded-xl bg-neutral-100" />
              ))}
            </div>
          ) : !data || data.items.length === 0 ? (
            <EmptyState
              icon={<Globe className="h-8 w-8" />}
              title="No matches yet"
              description="Investors will appear here once the matching engine scores your project against active mandates."
            />
          ) : filteredItems.length === 0 ? (
            <div className="flex h-40 items-center justify-center rounded-xl border border-dashed border-neutral-200">
              <p className="text-sm text-neutral-400">No investors match this filter.</p>
            </div>
          ) : (
            <div className="space-y-4">
              {filteredItems.map((investor) => (
                <InvestorCard
                  key={investor.investor_org_id}
                  investor={investor}
                  projectId={id}
                />
              ))}
              <p className="pt-1 text-center text-xs text-neutral-400">
                Showing {filteredItems.length} of {data.total} investor
                {data.total !== 1 ? "s" : ""}
              </p>
            </div>
          )}
        </div>

        {/* Right — activity timeline (1/3) */}
        <div>
          <Card className="sticky top-[calc(var(--topbar-height)+1.5rem)]">
            <CardContent className="p-5">
              <h2 className="mb-5 flex items-center gap-2 text-sm font-semibold text-neutral-900">
                <span className="flex h-6 w-6 items-center justify-center rounded-full bg-neutral-100">
                  <TrendingUp className="h-3.5 w-3.5 text-neutral-500" />
                </span>
                Match Activity
              </h2>
              {isLoading ? (
                <div className="space-y-4">
                  {[1, 2, 3].map((i) => (
                    <div key={i} className="h-12 animate-pulse rounded-lg bg-neutral-100" />
                  ))}
                </div>
              ) : (
                <ActivityTimeline investors={data?.items ?? []} />
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
