"use client";

import { useState, useMemo, useRef, useEffect } from "react";
import { useRouter } from "next/navigation";
import {
  ArrowRight,
  Check,
  ChevronDown,
  ChevronUp,
  Globe,
  MapPin,
  MoreHorizontal,
  Search,
  SlidersHorizontal,
  TrendingUp,
  Users,
  X,
  Zap,
} from "lucide-react";
import { Badge, cn } from "@scr/ui";
import {
  useUpdateMatchStatus,
  alignmentColor,
  alignmentBarColor,
  statusLabel,
  statusVariant,
  ALIGNMENT_DIMENSIONS,
  PIPELINE_STAGES,
  type MatchingInvestor,
} from "@/lib/matching";
import { InfoBanner } from "@/components/info-banner";

// ── Mock investor data ────────────────────────────────────────────────────────

const MOCK_INVESTORS: MatchingInvestor[] = [
  {
    match_id: "m-001",
    investor_org_id: "inv-001",
    investor_name: "GreenTech Ventures",
    logo_url: null,
    mandate_id: "mnd-001",
    mandate_name: "Clean Energy Fund III",
    ticket_size_min: "5000000",
    ticket_size_max: "20000000",
    sectors: ["solar", "wind", "energy_efficiency"],
    geographies: ["United States", "Canada", "United Kingdom"],
    risk_tolerance: "moderate",
    alignment: { overall: 96, sector: 24, geography: 18, ticket_size: 19, stage: 14, risk_return: 9, esg: 10, breakdown: {} },
    status: "suggested",
    initiated_by: null,
    updated_at: new Date(Date.now() - 2 * 86400000).toISOString(),
  },
  {
    match_id: "m-002",
    investor_org_id: "inv-002",
    investor_name: "Climate Capital Partners",
    logo_url: null,
    mandate_id: "mnd-002",
    mandate_name: "Impact ESG Mandate",
    ticket_size_min: "3000000",
    ticket_size_max: "12000000",
    sectors: ["solar", "sustainable_agriculture", "green_building"],
    geographies: ["United Kingdom", "Germany", "Netherlands"],
    risk_tolerance: "low",
    alignment: { overall: 94, sector: 23, geography: 19, ticket_size: 18, stage: 13, risk_return: 10, esg: 10, breakdown: {} },
    status: "interested",
    initiated_by: "investor",
    updated_at: new Date(Date.now() - 1 * 86400000).toISOString(),
  },
  {
    match_id: "m-003",
    investor_org_id: "inv-003",
    investor_name: "Meridian Infrastructure Fund",
    logo_url: null,
    mandate_id: "mnd-003",
    mandate_name: "Global Infrastructure IV",
    ticket_size_min: "10000000",
    ticket_size_max: "50000000",
    sectors: ["wind", "hydro", "geothermal"],
    geographies: ["Germany", "France", "Spain", "Italy"],
    risk_tolerance: "moderate",
    alignment: { overall: 89, sector: 22, geography: 17, ticket_size: 17, stage: 13, risk_return: 9, esg: 9, breakdown: {} },
    status: "viewed",
    initiated_by: null,
    updated_at: new Date(Date.now() - 4 * 86400000).toISOString(),
  },
  {
    match_id: "m-004",
    investor_org_id: "inv-004",
    investor_name: "Nordstern Capital",
    logo_url: null,
    mandate_id: "mnd-004",
    mandate_name: "Nordic Transition Fund",
    ticket_size_min: "2000000",
    ticket_size_max: "8000000",
    sectors: ["wind", "energy_efficiency", "biomass"],
    geographies: ["Sweden", "Norway", "Denmark", "Finland"],
    risk_tolerance: "low",
    alignment: { overall: 85, sector: 21, geography: 16, ticket_size: 16, stage: 12, risk_return: 9, esg: 10, breakdown: {} },
    status: "intro_requested",
    initiated_by: "ally",
    updated_at: new Date(Date.now() - 6 * 86400000).toISOString(),
  },
  {
    match_id: "m-005",
    investor_org_id: "inv-005",
    investor_name: "Sahara Growth Partners",
    logo_url: null,
    mandate_id: "mnd-005",
    mandate_name: "Emerging Markets Renewables",
    ticket_size_min: "1000000",
    ticket_size_max: "6000000",
    sectors: ["solar", "sustainable_agriculture"],
    geographies: ["Kenya", "Nigeria", "South Africa", "Morocco"],
    risk_tolerance: "high",
    alignment: { overall: 82, sector: 22, geography: 15, ticket_size: 15, stage: 11, risk_return: 9, esg: 9, breakdown: {} },
    status: "suggested",
    initiated_by: null,
    updated_at: null,
  },
  {
    match_id: "m-006",
    investor_org_id: "inv-006",
    investor_name: "Adriatic Infrastructure Holdings",
    logo_url: null,
    mandate_id: "mnd-006",
    mandate_name: "Southern Europe Energy Mandate",
    ticket_size_min: "8000000",
    ticket_size_max: "30000000",
    sectors: ["solar", "wind", "hydro"],
    geographies: ["Greece", "Croatia", "Serbia", "Romania"],
    risk_tolerance: "moderate",
    alignment: { overall: 79, sector: 20, geography: 16, ticket_size: 16, stage: 12, risk_return: 8, esg: 7, breakdown: {} },
    status: "engaged",
    initiated_by: "investor",
    updated_at: new Date(Date.now() - 3 * 86400000).toISOString(),
  },
  {
    match_id: "m-007",
    investor_org_id: "inv-007",
    investor_name: "Pacific Sustainability Fund",
    logo_url: null,
    mandate_id: "mnd-007",
    mandate_name: "Asia-Pacific Green Mandate",
    ticket_size_min: "5000000",
    ticket_size_max: "25000000",
    sectors: ["solar", "wind", "green_building"],
    geographies: ["Australia", "Japan", "South Korea", "Singapore"],
    risk_tolerance: "moderate",
    alignment: { overall: 76, sector: 19, geography: 14, ticket_size: 18, stage: 11, risk_return: 8, esg: 6, breakdown: {} },
    status: "suggested",
    initiated_by: null,
    updated_at: null,
  },
  {
    match_id: "m-008",
    investor_org_id: "inv-008",
    investor_name: "Nordic Biomass Energy Partners",
    logo_url: null,
    mandate_id: "mnd-008",
    mandate_name: "Bioenergy Transition Fund",
    ticket_size_min: "2000000",
    ticket_size_max: "10000000",
    sectors: ["biomass", "sustainable_agriculture", "energy_efficiency"],
    geographies: ["Sweden", "Finland", "Estonia", "Latvia"],
    risk_tolerance: "moderate",
    alignment: { overall: 73, sector: 18, geography: 15, ticket_size: 16, stage: 10, risk_return: 7, esg: 7, breakdown: {} },
    status: "suggested",
    initiated_by: null,
    updated_at: null,
  },
  {
    match_id: "m-009",
    investor_org_id: "inv-009",
    investor_name: "Thames Clean Energy Hub",
    logo_url: null,
    mandate_id: "mnd-009",
    mandate_name: "UK Low Carbon Fund",
    ticket_size_min: "4000000",
    ticket_size_max: "15000000",
    sectors: ["wind", "solar", "energy_efficiency", "green_building"],
    geographies: ["United Kingdom", "Ireland"],
    risk_tolerance: "low",
    alignment: { overall: 68, sector: 17, geography: 13, ticket_size: 15, stage: 10, risk_return: 7, esg: 6, breakdown: {} },
    status: "viewed",
    initiated_by: null,
    updated_at: new Date(Date.now() - 8 * 86400000).toISOString(),
  },
  {
    match_id: "m-010",
    investor_org_id: "inv-010",
    investor_name: "LatAm Renewables Capital",
    logo_url: null,
    mandate_id: "mnd-010",
    mandate_name: "Latin America Energy Transition",
    ticket_size_min: "3000000",
    ticket_size_max: "18000000",
    sectors: ["solar", "wind", "hydro"],
    geographies: ["Brazil", "Chile", "Colombia", "Mexico", "Peru"],
    risk_tolerance: "high",
    alignment: { overall: 64, sector: 16, geography: 12, ticket_size: 14, stage: 10, risk_return: 6, esg: 6, breakdown: {} },
    status: "passed",
    initiated_by: "ally",
    updated_at: new Date(Date.now() - 12 * 86400000).toISOString(),
  },
];

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
  return name.split(/\s+/).slice(0, 2).map((w) => w[0] ?? "").join("").toUpperCase();
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
    function onOut(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", onOut);
    return () => document.removeEventListener("mousedown", onOut);
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
                investor.status === stage.value ? "font-semibold text-[#1B2A4A]" : "text-neutral-700"
              )}
            >
              <span className="flex h-4 w-4 items-center justify-center">
                {investor.status === stage.value && <Check className="h-3.5 w-3.5 text-[#1B2A4A]" />}
              </span>
              {stage.label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Alignment breakdown ───────────────────────────────────────────────────────

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
              <span className={cn("font-semibold", alignmentColor(pct))}>{score}/{dim.max}</span>
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

// ── Investor detail modal ─────────────────────────────────────────────────────

function InvestorDetailModal({
  investor,
  onClose,
}: {
  investor: MatchingInvestor;
  onClose: () => void;
}) {
  const updateStatus = useUpdateMatchStatus();
  const { text, dot, ring } = matchScoreColor(investor.alignment.overall);
  const cta = primaryCTA(investor.status);

  const ticketMin = Number(investor.ticket_size_min);
  const ticketMax = Number(investor.ticket_size_max);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className="flex w-full max-w-2xl flex-col rounded-2xl bg-white shadow-2xl" style={{ maxHeight: "90vh" }}>
        {/* Header */}
        <div className="flex items-start justify-between gap-4 border-b border-neutral-100 p-6">
          <div className="flex items-center gap-4 min-w-0">
            <div className="flex h-14 w-14 shrink-0 items-center justify-center rounded-xl bg-[#1B2A4A]/8 text-lg font-bold text-[#1B2A4A]">
              {nameInitials(investor.investor_name)}
            </div>
            <div className="min-w-0">
              <h2 className="truncate text-xl font-bold text-neutral-900">{investor.investor_name}</h2>
              <p className="text-sm text-neutral-500">{investor.mandate_name ?? "Investment Fund"}</p>
            </div>
          </div>
          <div className="flex shrink-0 items-center gap-3">
            <div className={cn("flex items-center gap-1.5 rounded-full px-3 py-1.5 ring-1", ring)}>
              <span className={cn("h-2.5 w-2.5 rounded-full", dot)} />
              <span className={cn("text-lg font-bold tabular-nums", text)}>{investor.alignment.overall}%</span>
              <span className="text-sm text-neutral-400">match</span>
            </div>
            <button onClick={onClose} className="rounded-lg p-1.5 text-neutral-400 hover:bg-neutral-100">
              <X className="h-5 w-5" />
            </button>
          </div>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {/* Status + badge */}
          <div className="flex items-center gap-2">
            <Badge variant={statusVariant(investor.status)}>{statusLabel(investor.status)}</Badge>
            {investor.updated_at && (
              <span className="text-xs text-neutral-400">· Updated {relativeDate(investor.updated_at)}</span>
            )}
          </div>

          {/* Key facts grid */}
          <div className="grid grid-cols-2 gap-3">
            <div className="rounded-xl border border-neutral-100 bg-neutral-50 px-4 py-3">
              <p className="text-[10px] font-semibold uppercase tracking-wider text-neutral-400">Ticket Range</p>
              <p className="mt-1 text-base font-bold text-neutral-900">
                {fmtMoney(ticketMin)} – {fmtMoney(ticketMax)}
              </p>
            </div>
            <div className="rounded-xl border border-neutral-100 bg-neutral-50 px-4 py-3">
              <p className="text-[10px] font-semibold uppercase tracking-wider text-neutral-400">Risk Tolerance</p>
              <p className="mt-1 text-base font-bold text-neutral-900 capitalize">{investor.risk_tolerance}</p>
            </div>
            <div className="rounded-xl border border-neutral-100 bg-neutral-50 px-4 py-3">
              <p className="text-[10px] font-semibold uppercase tracking-wider text-neutral-400">Sectors</p>
              <p className="mt-1 text-sm font-semibold text-neutral-800">
                {investor.sectors.map((s) => s.replace(/_/g, " ")).join(", ") || "All sectors"}
              </p>
            </div>
            <div className="rounded-xl border border-neutral-100 bg-neutral-50 px-4 py-3">
              <p className="text-[10px] font-semibold uppercase tracking-wider text-neutral-400">Geographies</p>
              <p className="mt-1 text-sm font-semibold text-neutral-800">
                {investor.geographies.join(", ") || "Global"}
              </p>
            </div>
          </div>

          {/* Alignment breakdown */}
          <div>
            <h3 className="mb-3 text-sm font-semibold text-neutral-800">Alignment Breakdown</h3>
            <AlignmentBreakdown alignment={investor.alignment} />
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 border-t border-neutral-100 p-5">
          {cta && (
            <button
              disabled={!investor.match_id || updateStatus.isPending}
              onClick={() => {
                if (!investor.match_id) return;
                updateStatus.mutate({ matchId: investor.match_id, status: cta.nextStatus });
                onClose();
              }}
              className="rounded-lg bg-[#1B2A4A] px-5 py-2.5 text-sm font-medium text-white hover:bg-[#243660] disabled:opacity-50"
            >
              {cta.label}
            </button>
          )}
          <button
            onClick={onClose}
            className="rounded-lg border border-neutral-200 px-5 py-2.5 text-sm font-medium text-neutral-700 hover:bg-neutral-50"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Investor card ─────────────────────────────────────────────────────────────

function InvestorCard({
  investor,
  onSelect,
}: {
  investor: MatchingInvestor;
  onSelect: () => void;
}) {
  const updateStatus = useUpdateMatchStatus();
  const [showAlignment, setShowAlignment] = useState(false);
  const { text, dot, ring } = matchScoreColor(investor.alignment.overall);
  const cta = primaryCTA(investor.status);

  const ticketMin = Number(investor.ticket_size_min);
  const ticketMax = Number(investor.ticket_size_max);
  const ticketLabel = ticketMin || ticketMax ? `${fmtMoney(ticketMin)} – ${fmtMoney(ticketMax)}` : "—";

  const focusLabel =
    investor.sectors.length > 0
      ? investor.sectors.slice(0, 3).map((s) => s.replace(/_/g, " ")).join(", ") +
        (investor.sectors.length > 3 ? ` +${investor.sectors.length - 3}` : "")
      : "All sectors";

  const locationLabel =
    investor.geographies.length > 0
      ? investor.geographies.slice(0, 2).join(", ") +
        (investor.geographies.length > 2 ? ` +${investor.geographies.length - 2}` : "")
      : "Global";

  const chips = [
    ...investor.sectors.slice(0, 3).map((s) => s.replace(/_/g, " ")),
    investor.risk_tolerance
      ? investor.risk_tolerance.charAt(0).toUpperCase() + investor.risk_tolerance.slice(1) + " Risk"
      : "",
  ].filter(Boolean);

  return (
    <div className="group rounded-xl border border-neutral-200 bg-white shadow-sm transition-shadow hover:shadow-md">
      <div className="p-5">
        {/* Top row */}
        <div className="flex items-start justify-between gap-4">
          <div className="flex cursor-pointer items-center gap-3 min-w-0" onClick={onSelect}>
            <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-[#1B2A4A]/8 text-sm font-bold text-[#1B2A4A]">
              {nameInitials(investor.investor_name)}
            </div>
            <div className="min-w-0">
              <h3 className="truncate font-semibold text-neutral-900">{investor.investor_name}</h3>
              <p className="truncate text-sm text-neutral-500">{investor.mandate_name ?? "Investment Fund"}</p>
            </div>
          </div>

          <div className="flex shrink-0 items-start gap-2">
            <div className="flex flex-col items-end gap-1.5">
              <div className={cn("flex items-center gap-1.5 rounded-full px-2.5 py-1 ring-1", ring)}>
                <span className={cn("h-2 w-2 rounded-full", dot)} />
                <span className={cn("text-sm font-bold tabular-nums", text)}>{investor.alignment.overall}%</span>
                <span className="text-xs text-neutral-400">match</span>
              </div>
              <Badge variant={statusVariant(investor.status)} className="text-xs">
                {statusLabel(investor.status)}
              </Badge>
            </div>
            <StatusMenu investor={investor} />
          </div>
        </div>

        {/* Info row */}
        <div className="mt-4 grid grid-cols-2 gap-3">
          <div className="rounded-lg bg-neutral-50 px-3 py-2">
            <p className="text-[10px] font-medium uppercase tracking-wider text-neutral-400">Investment Focus</p>
            <p className="mt-0.5 truncate text-sm font-medium text-neutral-800">{focusLabel}</p>
          </div>
          <div className="rounded-lg bg-neutral-50 px-3 py-2">
            <p className="text-[10px] font-medium uppercase tracking-wider text-neutral-400">Ticket Size</p>
            <p className="mt-0.5 text-sm font-medium text-neutral-800">{ticketLabel}</p>
          </div>
        </div>

        {/* Location */}
        <div className="mt-3 flex items-center gap-1.5 text-sm text-neutral-500">
          <MapPin className="h-3.5 w-3.5 shrink-0 text-neutral-400" />
          <span>{locationLabel}</span>
        </div>

        {/* Chips */}
        {chips.length > 0 && (
          <div className="mt-3 flex flex-wrap gap-1.5">
            {chips.map((chip) => (
              <span key={chip} className="inline-flex items-center rounded-full border border-neutral-200 bg-white px-2.5 py-0.5 text-xs text-neutral-600">
                {chip}
              </span>
            ))}
          </div>
        )}

        {/* Alignment toggle */}
        <button
          onClick={() => setShowAlignment((v) => !v)}
          className="mt-4 flex items-center gap-1 text-xs font-medium text-neutral-400 hover:text-neutral-700"
        >
          {showAlignment ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
          {showAlignment ? "Hide" : "See"} alignment breakdown
        </button>

        {showAlignment && (
          <div className="mt-3 rounded-lg border border-neutral-100 bg-neutral-50 p-4">
            <div className="mb-3 flex items-center justify-between">
              <p className="text-xs font-semibold text-neutral-700">Alignment Breakdown</p>
              <span className={cn("text-sm font-bold tabular-nums", alignmentColor(investor.alignment.overall))}>
                {investor.alignment.overall}% overall
              </span>
            </div>
            <AlignmentBreakdown alignment={investor.alignment} />
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="flex items-center gap-3 border-t border-neutral-100 px-5 py-3">
        {cta ? (
          <button
            disabled={!investor.match_id || updateStatus.isPending}
            onClick={() => {
              if (!investor.match_id) return;
              updateStatus.mutate({ matchId: investor.match_id, status: cta.nextStatus });
            }}
            className="flex-1 rounded-lg bg-[#1B2A4A] py-2 text-sm font-medium text-white transition-colors hover:bg-[#243660] disabled:opacity-50"
          >
            {cta.label}
          </button>
        ) : (
          <div className="flex-1" />
        )}
        <button
          onClick={onSelect}
          className="flex items-center gap-1 text-sm font-medium text-neutral-500 transition-colors hover:text-[#1B2A4A]"
        >
          View Profile
          <ArrowRight className="h-3.5 w-3.5" />
        </button>
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

const SECTOR_OPTIONS = [
  { value: "", label: "All Sectors" },
  { value: "solar", label: "Solar" },
  { value: "wind", label: "Wind" },
  { value: "hydro", label: "Hydro" },
  { value: "biomass", label: "Biomass" },
  { value: "geothermal", label: "Geothermal" },
  { value: "energy_efficiency", label: "Energy Efficiency" },
  { value: "green_building", label: "Green Building" },
  { value: "sustainable_agriculture", label: "Sustainable Agriculture" },
];

// ── Page ──────────────────────────────────────────────────────────────────────

export default function MatchingPage() {
  const router = useRouter();
  const [filter, setFilter] = useState<FilterKey>("all");
  const [sort, setSort] = useState<SortKey>("best_match");
  const [search, setSearch] = useState("");
  const [sectorFilter, setSectorFilter] = useState("");
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [selectedInvestor, setSelectedInvestor] = useState<MatchingInvestor | null>(null);

  // ── Stats ──────────────────────────────────────────────────────────────────
  const stats = useMemo(() => {
    const interested = MOCK_INVESTORS.filter((i) =>
      ["interested", "intro_requested", "engaged"].includes(i.status)
    ).length;
    const avgMatch = Math.round(
      MOCK_INVESTORS.reduce((s, i) => s + i.alignment.overall, 0) / MOCK_INVESTORS.length
    );
    const highMatch = MOCK_INVESTORS.filter((i) => i.alignment.overall >= 80).length;
    return { total: MOCK_INVESTORS.length, interested, avgMatch, highMatch };
  }, []);

  // ── Filtered list ──────────────────────────────────────────────────────────
  const filteredItems = useMemo(() => {
    let items = [...MOCK_INVESTORS];

    // Search
    if (search.trim()) {
      const q = search.toLowerCase();
      items = items.filter(
        (i) =>
          i.investor_name.toLowerCase().includes(q) ||
          (i.mandate_name ?? "").toLowerCase().includes(q) ||
          i.sectors.some((s) => s.includes(q)) ||
          i.geographies.some((g) => g.toLowerCase().includes(q))
      );
    }

    // Sector filter
    if (sectorFilter) {
      items = items.filter((i) => i.sectors.includes(sectorFilter));
    }

    // Status filter
    switch (filter) {
      case "high_match":
        items = items.filter((i) => i.alignment.overall >= 80);
        break;
      case "interested":
        items = items.filter((i) => ["interested", "intro_requested"].includes(i.status));
        break;
      case "engaged":
        items = items.filter((i) => i.status === "engaged");
        break;
    }

    // Sort
    if (sort === "best_match") {
      items.sort((a, b) => b.alignment.overall - a.alignment.overall);
    } else {
      items.sort((a, b) => {
        const aT = a.updated_at ? new Date(a.updated_at).getTime() : 0;
        const bT = b.updated_at ? new Date(b.updated_at).getTime() : 0;
        return bT - aT;
      });
    }

    return items;
  }, [filter, sort, search, sectorFilter]);

  return (
    <div className="mx-auto max-w-screen-xl p-6">

      {/* ── Header ──────────────────────────────────────────────────────── */}
      <div className="mb-6 flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-neutral-900">Investor Matching</h1>
          <p className="mt-1 text-sm text-neutral-500">
            AI-powered smart syndication and allocation — find the best-fit investors for your projects.
          </p>
        </div>
        <button
          onClick={() => router.push("/projects")}
          className="flex shrink-0 items-center gap-1.5 rounded-lg border border-neutral-200 bg-white px-4 py-2 text-sm font-medium text-neutral-700 transition-colors hover:bg-neutral-50"
        >
          <Zap className="h-3.5 w-3.5 text-amber-500" />
          Run Matching Engine
        </button>
      </div>

      <InfoBanner className="mb-6">
        <strong>Investor Matching</strong> pairs your projects with compatible investors based on mandate alignment, geography, asset class, ticket size, and ESG criteria. Each match includes a <strong>compatibility score</strong> with clear explanations of what&apos;s driving the recommendation.
      </InfoBanner>

      {/* ── Stats strip ─────────────────────────────────────────────────── */}
      <div className="mb-6 grid grid-cols-2 divide-x divide-neutral-100 overflow-hidden rounded-xl border border-neutral-200 bg-white shadow-sm sm:grid-cols-4">
        {[
          { label: "Total Investors", value: stats.total, icon: Users },
          { label: "Interested", value: stats.interested, icon: TrendingUp, color: "text-green-600" },
          { label: "Avg. Match Score", value: `${stats.avgMatch}%`, icon: null },
          { label: "High Match (≥80%)", value: stats.highMatch, icon: null, color: "text-blue-600" },
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

      {/* ── Search + filter bar ──────────────────────────────────────────── */}
      <div className="mb-4 space-y-3">
        {/* Search row */}
        <div className="flex items-center gap-3">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-neutral-400" />
            <input
              type="text"
              placeholder="Search by investor name, sector, geography…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full rounded-lg border border-neutral-200 bg-white py-2.5 pl-9 pr-4 text-sm text-neutral-800 placeholder:text-neutral-400 focus:outline-none focus:ring-2 focus:ring-[#1B2A4A]/20"
            />
            {search && (
              <button onClick={() => setSearch("")} className="absolute right-3 top-1/2 -translate-y-1/2">
                <X className="h-4 w-4 text-neutral-400 hover:text-neutral-600" />
              </button>
            )}
          </div>
          <button
            onClick={() => setShowAdvanced((v) => !v)}
            className={cn(
              "flex items-center gap-1.5 rounded-lg border px-3 py-2.5 text-sm font-medium transition-colors",
              showAdvanced
                ? "border-[#1B2A4A] bg-[#1B2A4A]/5 text-[#1B2A4A]"
                : "border-neutral-200 bg-white text-neutral-600 hover:bg-neutral-50"
            )}
          >
            <SlidersHorizontal className="h-4 w-4" />
            Filters
          </button>
        </div>

        {/* Advanced filters */}
        {showAdvanced && (
          <div className="rounded-xl border border-neutral-200 bg-neutral-50 p-4">
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
              <div>
                <label className="mb-1 block text-xs font-medium text-neutral-600">Sector</label>
                <select
                  value={sectorFilter}
                  onChange={(e) => setSectorFilter(e.target.value)}
                  className="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm text-neutral-800 focus:outline-none"
                >
                  {SECTOR_OPTIONS.map((o) => (
                    <option key={o.value} value={o.value}>{o.label}</option>
                  ))}
                </select>
              </div>
            </div>
            <div className="mt-3 flex justify-end">
              <button
                onClick={() => { setSectorFilter(""); setShowAdvanced(false); }}
                className="text-xs text-neutral-400 hover:text-neutral-700"
              >
                Clear filters
              </button>
            </div>
          </div>
        )}

        {/* Filter pills + sort */}
        <div className="flex flex-wrap items-center justify-between gap-3">
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
      </div>

      {/* ── Results ─────────────────────────────────────────────────────── */}
      {filteredItems.length === 0 ? (
        <div className="flex h-48 items-center justify-center rounded-xl border border-dashed border-neutral-200">
          <div className="text-center">
            <Globe className="mx-auto mb-2 h-8 w-8 text-neutral-300" />
            <p className="text-sm text-neutral-500">No investors match your current filters.</p>
            <button
              onClick={() => { setFilter("all"); setSearch(""); setSectorFilter(""); }}
              className="mt-2 text-xs text-[#1B2A4A] hover:underline"
            >
              Clear all filters
            </button>
          </div>
        </div>
      ) : (
        <>
          <p className="mb-4 text-xs text-neutral-400">
            Showing {filteredItems.length} of {MOCK_INVESTORS.length} investors
          </p>
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
            {filteredItems.map((investor) => (
              <InvestorCard
                key={investor.investor_org_id}
                investor={investor}
                onSelect={() => setSelectedInvestor(investor)}
              />
            ))}
          </div>
        </>
      )}

      {/* ── Detail modal ────────────────────────────────────────────────── */}
      {selectedInvestor && (
        <InvestorDetailModal
          investor={selectedInvestor}
          onClose={() => setSelectedInvestor(null)}
        />
      )}
    </div>
  );
}
