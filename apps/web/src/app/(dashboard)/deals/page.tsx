"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import {
  Globe,
  Search,
  SlidersHorizontal,
  CheckSquare,
  Square,
  ChevronRight,
  TrendingUp,
  Filter,
  ArrowUpRight,
  Clock,
  DollarSign,
  Target,
} from "lucide-react";
import {
  Badge,
  Button,
  Card,
  CardContent,
  InfoBanner,
  LoadingSpinner,
  ScoreGauge,
  Tabs,
  TabsList,
  TabsTrigger,
  TabsContent,
} from "@scr/ui";
import {
  useDealPipeline,
  useDiscoverDeals,
  useCompareProjects,
  useUpdateDealStatus,
  alignmentColor,
  PIPELINE_STATUS_OPTIONS,
  type DealCard,
  type DiscoveryDeal,
  type CompareResponse,
  type DiscoverParams,
} from "@/lib/deals";
import { formatCurrency } from "@/lib/projects";

// ── Mock data ─────────────────────────────────────────────────────────────

const MOCK_PIPELINE_DATA = {
  discovered: [] as DealCard[],
  screening: [
    {
      project_id: "p1", match_id: "m-p1", project_name: "Sahara CSP Development",
      project_type: "solar", geography_country: "Morocco", stage: "screening",
      total_investment_required: "65000000", currency: "EUR",
      signal_score: 58, alignment_score: 62, status: "viewed", cover_image_url: null,
      updated_at: new Date(Date.now() - 2 * 86400000).toISOString(),
    },
    {
      project_id: "p5", match_id: "m-p5", project_name: "Porto Solar Park",
      project_type: "solar", geography_country: "Portugal", stage: "screening",
      total_investment_required: "35000000", currency: "EUR",
      signal_score: 81, alignment_score: 78, status: "viewed", cover_image_url: null,
      updated_at: new Date(Date.now() - 1 * 86400000).toISOString(),
    },
    {
      project_id: "p8", match_id: "m-p8", project_name: "East Aegean Solar",
      project_type: "solar", geography_country: "Greece", stage: "screening",
      total_investment_required: "28000000", currency: "EUR",
      signal_score: 71, alignment_score: 74, status: "suggested", cover_image_url: null,
      updated_at: new Date(Date.now() - 5 * 86400000).toISOString(),
    },
  ] as DealCard[],
  due_diligence: [
    {
      project_id: "p2", match_id: "m-p2", project_name: "Danube Hydro Expansion",
      project_type: "hydro", geography_country: "Romania", stage: "due_diligence",
      total_investment_required: "28000000", currency: "EUR",
      signal_score: 72, alignment_score: 75, status: "interested", cover_image_url: null,
      updated_at: new Date(Date.now() - 3 * 86400000).toISOString(),
    },
    {
      project_id: "p3", match_id: "m-p3", project_name: "Aegean Wind Cluster",
      project_type: "wind", geography_country: "Greece", stage: "due_diligence",
      total_investment_required: "42000000", currency: "EUR",
      signal_score: 69, alignment_score: 71, status: "interested", cover_image_url: null,
      updated_at: new Date(Date.now() - 4 * 86400000).toISOString(),
    },
  ] as DealCard[],
  negotiation: [
    {
      project_id: "p4", match_id: "m-p4", project_name: "Bavarian Biomass Network",
      project_type: "biomass", geography_country: "Germany", stage: "negotiation",
      total_investment_required: "15000000", currency: "EUR",
      signal_score: 76, alignment_score: 80, status: "intro_requested", cover_image_url: null,
      updated_at: new Date(Date.now() - 1 * 86400000).toISOString(),
    },
    {
      project_id: "p9", match_id: "m-p9", project_name: "Alpine Hydro Partners",
      project_type: "hydro", geography_country: "Switzerland", stage: "negotiation",
      total_investment_required: "52000000", currency: "EUR",
      signal_score: 91, alignment_score: 88, status: "intro_requested", cover_image_url: null,
      updated_at: new Date(Date.now() - 2 * 86400000).toISOString(),
    },
  ] as DealCard[],
  passed: [
    {
      project_id: "p6", match_id: "m-p6", project_name: "Sahara CSP Phase II",
      project_type: "solar", geography_country: "Algeria", stage: "screening",
      total_investment_required: "90000000", currency: "EUR",
      signal_score: 44, alignment_score: 38, status: "passed", cover_image_url: null,
      updated_at: new Date(Date.now() - 10 * 86400000).toISOString(),
    },
  ] as DealCard[],
};

const MOCK_DISCOVER_RESPONSE = {
  items: [
    {
      project_id: "d1", project_name: "Aegean Solar Extension",
      project_type: "solar", geography_country: "Greece", stage: "development",
      total_investment_required: "22000000", currency: "EUR",
      signal_score: 66, alignment_score: 68,
      alignment_reasons: ["Sector match", "EU geography", "Score ≥60"],
      cover_image_url: null, is_in_pipeline: false,
    },
    {
      project_id: "d2", project_name: "Finnish Wind Portfolio",
      project_type: "wind", geography_country: "Finland", stage: "development",
      total_investment_required: "55000000", currency: "EUR",
      signal_score: 74, alignment_score: 76,
      alignment_reasons: ["Wind sector match", "Nordic geography", "Strong IRR profile"],
      cover_image_url: null, is_in_pipeline: false,
    },
    {
      project_id: "d3", project_name: "Moroccan Green Hydrogen",
      project_type: "other", geography_country: "Morocco", stage: "concept",
      total_investment_required: "120000000", currency: "EUR",
      signal_score: 52, alignment_score: 55,
      alignment_reasons: ["Emerging market growth", "Green H2 policy momentum"],
      cover_image_url: null, is_in_pipeline: false,
    },
    {
      project_id: "d4", project_name: "Polish Biomass Cluster",
      project_type: "biomass", geography_country: "Poland", stage: "permitting",
      total_investment_required: "18000000", currency: "EUR",
      signal_score: 63, alignment_score: 65,
      alignment_reasons: ["Biomass sector", "EU cohesion market", "Grid-connected"],
      cover_image_url: null, is_in_pipeline: false,
    },
    {
      project_id: "d5", project_name: "Czech Hydro Upgrade",
      project_type: "hydro", geography_country: "Czech Republic", stage: "development",
      total_investment_required: "9000000", currency: "EUR",
      signal_score: 70, alignment_score: 72,
      alignment_reasons: ["Hydro sector match", "Central Europe", "Operational upgrade"],
      cover_image_url: null, is_in_pipeline: false,
    },
    {
      project_id: "d6", project_name: "Nordvik Offshore Wind II",
      project_type: "wind", geography_country: "Norway", stage: "development",
      total_investment_required: "85000000", currency: "EUR",
      signal_score: 83, alignment_score: 81,
      alignment_reasons: ["Strong wind resource", "Offtake agreement signed", "Tier-1 sponsor"],
      cover_image_url: null, is_in_pipeline: false,
    },
  ] as DiscoveryDeal[],
  total: 6,
  mandate_name: "European Renewables Fund Mandate",
};

const MOCK_COMPARE_RESULT: CompareResponse = {
  project_ids: ["p2", "p3", "p4"],
  project_names: ["Danube Hydro Expansion", "Aegean Wind Cluster", "Bavarian Biomass Network"],
  rows: [
    { dimension: "Signal Score",    values: [72, 69, 76],              best_index: 2, worst_index: 1 },
    { dimension: "IRR (%)",         values: ["11.8%", "10.4%", "12.1%"], best_index: 2, worst_index: 1 },
    { dimension: "Target Size",     values: ["€28M", "€42M", "€15M"],    best_index: null, worst_index: null },
    { dimension: "Sector",          values: ["Hydro", "Wind", "Biomass"],  best_index: null, worst_index: null },
    { dimension: "Geography",       values: ["Romania", "Greece", "Germany"], best_index: 2, worst_index: null },
    { dimension: "Stage",           values: ["Due Diligence", "Due Diligence", "Negotiation"], best_index: 2, worst_index: null },
    { dimension: "Alignment Score", values: [75, 71, 80],              best_index: 2, worst_index: 1 },
    { dimension: "Risk Score",      values: [68, 65, 72],              best_index: 2, worst_index: 1 },
    { dimension: "ESG Score",       values: [74, 68, 71],              best_index: 0, worst_index: 1 },
    { dimension: "Payback (yrs)",   values: [8, 10, 7],                best_index: 2, worst_index: 1 },
  ],
};

// ── Helpers ────────────────────────────────────────────────────────────────

const TYPE_COLORS: Record<string, string> = {
  solar: "from-amber-400 to-orange-500",
  wind: "from-sky-400 to-blue-500",
  hydro: "from-blue-400 to-cyan-500",
  biomass: "from-green-500 to-emerald-600",
  geothermal: "from-red-400 to-orange-600",
  energy_efficiency: "from-purple-400 to-violet-600",
  green_building: "from-teal-400 to-green-600",
  sustainable_agriculture: "from-lime-400 to-green-500",
  other: "from-neutral-400 to-neutral-600",
};

const STAGE_META: Record<string, { label: string; color: string; bg: string; border: string }> = {
  discovered:    { label: "Sourced",       color: "text-neutral-600", bg: "bg-neutral-50",  border: "border-neutral-200" },
  screening:     { label: "Screening",     color: "text-blue-700",    bg: "bg-blue-50",     border: "border-blue-200" },
  due_diligence: { label: "Due Diligence", color: "text-amber-700",   bg: "bg-amber-50",    border: "border-amber-200" },
  negotiation:   { label: "Negotiation",  color: "text-indigo-700",  bg: "bg-indigo-50",   border: "border-indigo-200" },
  passed:        { label: "Passed",        color: "text-neutral-500", bg: "bg-neutral-50",  border: "border-neutral-200" },
};

function typeGradient(type: string): string {
  return TYPE_COLORS[type] ?? TYPE_COLORS.other;
}

function typeLabel(type: string): string {
  return type.split("_").map((w) => w.charAt(0).toUpperCase() + w.slice(1)).join(" ");
}

function stageIcon(stage: string) {
  const map: Record<string, string> = {
    discovered: "●", screening: "◎", due_diligence: "◉", negotiation: "◈", passed: "○",
  };
  return map[stage] ?? "●";
}

// ── Pipeline column ────────────────────────────────────────────────────────

const PIPELINE_COLUMNS = [
  { key: "discovered", label: "Sourced" },
  { key: "screening", label: "Screening" },
  { key: "due_diligence", label: "Due Diligence" },
  { key: "negotiation", label: "Negotiation" },
  { key: "passed", label: "Passed" },
] as const;

function PipelineCard({ card }: { card: DealCard }) {
  const router = useRouter();
  const updateStatus = useUpdateDealStatus();
  const gradient = typeGradient(card.project_type);

  return (
    <div className="group rounded-xl border border-neutral-200 bg-white hover:border-primary-300 hover:shadow-md transition-all cursor-pointer overflow-hidden">
      {/* Thin color band */}
      <div className={`h-1.5 bg-gradient-to-r ${gradient}`} />

      <div className="p-3">
        {/* Header row: name + score circle */}
        <div className="flex items-start justify-between gap-2 mb-2">
          <p
            className="font-semibold text-sm leading-tight line-clamp-2 flex-1 text-neutral-900 group-hover:text-primary-700 transition-colors"
            onClick={() => router.push(`/deals/${card.project_id}`)}
          >
            {card.project_name}
          </p>
          {card.signal_score != null && (
            <ScoreGauge score={card.signal_score} size={44} strokeWidth={5} fullCircle label="" />
          )}
        </div>

        {/* Meta */}
        <div className="flex items-center gap-1.5 text-xs text-neutral-500 mb-1">
          <Globe className="h-3 w-3 shrink-0" />
          <span className="truncate">{card.geography_country}</span>
          <span className="text-neutral-300">·</span>
          <span className="truncate">{typeLabel(card.project_type)}</span>
        </div>

        {/* Size + stage */}
        <div className="flex items-center justify-between mb-2.5">
          <span className="text-xs font-semibold text-neutral-800">
            {formatCurrency(Number(card.total_investment_required), card.currency)}
          </span>
          <span className="text-[10px] text-neutral-400">
            {new Date(card.updated_at).toLocaleDateString("en-GB", { day: "numeric", month: "short" })}
          </span>
        </div>

        {/* Alignment bar */}
        <div className="mb-3">
          <div className="flex justify-between text-[10px] mb-1">
            <span className="text-neutral-400 font-medium uppercase tracking-wide">Alignment</span>
            <span className={`font-semibold ${alignmentColor(card.alignment_score)}`}>
              {card.alignment_score}%
            </span>
          </div>
          <div className="h-1 bg-neutral-100 rounded-full overflow-hidden">
            <div
              className={`h-full rounded-full ${
                card.alignment_score >= 70 ? "bg-green-500" :
                card.alignment_score >= 40 ? "bg-amber-500" : "bg-red-400"
              }`}
              style={{ width: `${card.alignment_score}%` }}
            />
          </div>
        </div>

        {/* Actions */}
        <div className="flex gap-1.5">
          <Button
            size="sm"
            variant="outline"
            className="flex-1 text-xs h-7 font-medium"
            onClick={() => router.push(`/deals/${card.project_id}`)}
          >
            Screen <ChevronRight className="h-3 w-3 ml-0.5" />
          </Button>
          <select
            className="text-xs border border-neutral-200 rounded-md px-1.5 h-7 bg-white text-neutral-600 focus:ring-1 focus:ring-primary-400 focus:outline-none"
            value={card.status}
            onClick={(e) => e.stopPropagation()}
            onChange={(e) =>
              updateStatus.mutate({ projectId: card.project_id, status: e.target.value })
            }
          >
            {PIPELINE_STATUS_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>
        </div>
      </div>
    </div>
  );
}

function PipelineTab() {
  const { data: apiData, isLoading } = useDealPipeline();

  if (isLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <LoadingSpinner />
      </div>
    );
  }

  const data = apiData ?? MOCK_PIPELINE_DATA;

  const columnData: Record<string, DealCard[]> = {
    discovered: data.discovered,
    screening: data.screening,
    due_diligence: data.due_diligence,
    negotiation: data.negotiation,
    passed: data.passed,
  };

  // Pipeline stats
  const allDeals = Object.values(columnData).flat();
  const totalValue = allDeals.reduce((s, c) => s + Number(c.total_investment_required), 0);
  const activeDeals = allDeals.filter((c) => c.stage !== "passed").length;

  return (
    <div className="space-y-4">
      {/* Stats bar */}
      <div className="grid grid-cols-3 sm:grid-cols-5 gap-3">
        {[
          { label: "Active Deals", value: activeDeals, icon: Target, color: "text-primary-600" },
          { label: "Pipeline Value", value: formatCurrency(totalValue, "EUR"), icon: DollarSign, color: "text-green-600" },
          { label: "Screening", value: columnData.screening.length, icon: Search, color: "text-blue-600" },
          { label: "Due Diligence", value: columnData.due_diligence.length, icon: Filter, color: "text-amber-600" },
          { label: "Negotiation", value: columnData.negotiation.length, icon: TrendingUp, color: "text-indigo-600" },
        ].map(({ label, value, icon: Icon, color }) => (
          <div key={label} className="rounded-xl border border-neutral-100 bg-white px-4 py-3 shadow-sm">
            <div className="flex items-center gap-2 mb-1">
              <Icon className={`h-3.5 w-3.5 ${color}`} />
              <span className="text-[10px] font-semibold uppercase tracking-wider text-neutral-400">{label}</span>
            </div>
            <p className="text-lg font-bold text-neutral-900">{value}</p>
          </div>
        ))}
      </div>

      {/* Kanban board */}
      <div className="overflow-x-auto">
        <div className="flex gap-3 min-w-[900px] pb-4">
          {PIPELINE_COLUMNS.map((col) => {
            const cards = columnData[col.key] ?? [];
            const meta = STAGE_META[col.key];
            const colValue = cards.reduce((s, c) => s + Number(c.total_investment_required), 0);

            return (
              <div key={col.key} className="flex-1 min-w-[185px]">
                {/* Column header */}
                <div className={`rounded-xl border ${meta.border} ${meta.bg} px-3 py-2 mb-2.5`}>
                  <div className="flex items-center justify-between mb-0.5">
                    <span className={`text-xs font-bold uppercase tracking-wide ${meta.color}`}>
                      {stageIcon(col.key)} {col.label}
                    </span>
                    <Badge variant="neutral" className="text-xs font-semibold h-5">{cards.length}</Badge>
                  </div>
                  {colValue > 0 && (
                    <p className="text-[10px] text-neutral-500 font-medium">
                      {formatCurrency(colValue, "EUR")}
                    </p>
                  )}
                </div>

                {/* Cards */}
                <div className="min-h-[200px] space-y-2">
                  {cards.length === 0 ? (
                    <div className="flex items-center justify-center h-20 rounded-lg border border-dashed border-neutral-200 text-xs text-neutral-300">
                      No deals
                    </div>
                  ) : (
                    cards.map((card) => <PipelineCard key={card.match_id} card={card} />)
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

// ── Discovery tab ──────────────────────────────────────────────────────────

function DiscoveryCard({
  deal,
  isSelected,
  onToggleCompare,
}: {
  deal: DiscoveryDeal;
  isSelected: boolean;
  onToggleCompare: () => void;
}) {
  const router = useRouter();
  const updateStatus = useUpdateDealStatus();
  const gradient = typeGradient(deal.project_type);

  return (
    <Card className="overflow-hidden hover:shadow-md transition-shadow">
      {/* Cover gradient */}
      <div className={`h-28 bg-gradient-to-br ${gradient} relative`}>
        <div className="absolute inset-0 flex items-end justify-between p-3">
          <Badge variant="neutral" className="text-xs bg-white/90 text-neutral-700 font-medium">
            {typeLabel(deal.project_type)}
          </Badge>
          <Badge variant="neutral" className="text-xs bg-white/90 text-neutral-700 capitalize">
            {deal.stage.replace("_", " ")}
          </Badge>
        </div>
      </div>

      <CardContent className="p-4">
        <div className="flex items-start justify-between gap-2 mb-2">
          <h3 className="font-semibold text-sm leading-tight line-clamp-2 flex-1 text-neutral-900">
            {deal.project_name}
          </h3>
          {deal.signal_score != null && (
            <ScoreGauge score={deal.signal_score} size={48} strokeWidth={5} fullCircle label="" />
          )}
        </div>

        <div className="flex items-center gap-2 text-xs text-neutral-500 mb-2">
          <Globe className="h-3 w-3" />
          <span>{deal.geography_country}</span>
        </div>

        <p className="text-sm font-bold text-neutral-900 mb-3">
          {formatCurrency(Number(deal.total_investment_required), deal.currency)}
        </p>

        {/* Alignment */}
        <div className="mb-3">
          <div className="flex justify-between text-xs mb-1">
            <span className="text-neutral-500 font-medium">Mandate Alignment</span>
            <span className={`font-semibold ${alignmentColor(deal.alignment_score)}`}>
              {deal.alignment_score}%
            </span>
          </div>
          <div className="h-1.5 bg-neutral-100 rounded-full overflow-hidden">
            <div
              className={`h-full rounded-full ${
                deal.alignment_score >= 70 ? "bg-green-500" :
                deal.alignment_score >= 40 ? "bg-amber-500" : "bg-red-400"
              }`}
              style={{ width: `${deal.alignment_score}%` }}
            />
          </div>
          {deal.alignment_reasons && deal.alignment_reasons.length > 0 && (
            <div className="flex flex-wrap gap-1 mt-1.5">
              {deal.alignment_reasons.slice(0, 2).map((r) => (
                <span key={r} className="text-[10px] bg-neutral-100 text-neutral-500 rounded px-1.5 py-0.5">
                  {r}
                </span>
              ))}
            </div>
          )}
        </div>

        <div className="flex gap-2">
          <button
            onClick={onToggleCompare}
            className="flex items-center gap-1 text-xs text-neutral-500 hover:text-primary-600 transition-colors"
          >
            {isSelected ? (
              <CheckSquare className="h-4 w-4 text-primary-600" />
            ) : (
              <Square className="h-4 w-4" />
            )}
            Compare
          </button>
          <Button
            size="sm"
            variant="outline"
            className="flex-1 text-xs h-7"
            onClick={() => router.push(`/deals/${deal.project_id}`)}
          >
            Screen <ArrowUpRight className="h-3 w-3 ml-1" />
          </Button>
          {!deal.is_in_pipeline && (
            <Button
              size="sm"
              className="text-xs h-7 font-medium"
              onClick={() => updateStatus.mutate({ projectId: deal.project_id, status: "suggested" })}
            >
              + Pipeline
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

function DiscoverTab({
  selectedIds,
  onToggleCompare,
}: {
  selectedIds: string[];
  onToggleCompare: (id: string) => void;
}) {
  const [filters, setFilters] = useState<DiscoverParams>({});
  const [applied, setApplied] = useState<DiscoverParams>({});

  const { data: apiData, isLoading } = useDiscoverDeals(applied);
  const handleApply = () => setApplied({ ...filters });

  const data = apiData && apiData.items.length > 0 ? apiData : MOCK_DISCOVER_RESPONSE;

  return (
    <div>
      {/* Filter row */}
      <div className="flex flex-wrap gap-3 mb-6 p-4 bg-neutral-50 rounded-xl border border-neutral-200">
        <div className="flex items-center gap-2">
          <SlidersHorizontal className="h-4 w-4 text-neutral-500" />
          <span className="text-sm font-semibold text-neutral-600">Filters</span>
        </div>
        <select
          className="text-sm border border-neutral-200 rounded-lg px-3 py-1.5 bg-white focus:ring-2 focus:ring-primary-400 focus:outline-none"
          value={filters.sector ?? ""}
          onChange={(e) => setFilters((f) => ({ ...f, sector: e.target.value || undefined }))}
        >
          <option value="">All Sectors</option>
          <option value="solar">Solar</option>
          <option value="wind">Wind</option>
          <option value="hydro">Hydro</option>
          <option value="biomass">Biomass</option>
          <option value="geothermal">Geothermal</option>
          <option value="energy_efficiency">Energy Efficiency</option>
          <option value="green_building">Green Building</option>
          <option value="sustainable_agriculture">Sustainable Agriculture</option>
        </select>
        <input
          type="text"
          placeholder="Geography..."
          className="text-sm border border-neutral-200 rounded-lg px-3 py-1.5 w-36 focus:ring-2 focus:ring-primary-400 focus:outline-none"
          value={filters.geography ?? ""}
          onChange={(e) => setFilters((f) => ({ ...f, geography: e.target.value || undefined }))}
        />
        <div className="flex items-center gap-1.5">
          <input
            type="number"
            placeholder="Min score"
            className="text-sm border border-neutral-200 rounded-lg px-2.5 py-1.5 w-24 focus:ring-2 focus:ring-primary-400 focus:outline-none"
            min={0} max={100}
            value={filters.score_min ?? ""}
            onChange={(e) => setFilters((f) => ({ ...f, score_min: e.target.value ? Number(e.target.value) : undefined }))}
          />
          <span className="text-neutral-300 text-sm">–</span>
          <input
            type="number"
            placeholder="Max score"
            className="text-sm border border-neutral-200 rounded-lg px-2.5 py-1.5 w-24 focus:ring-2 focus:ring-primary-400 focus:outline-none"
            min={0} max={100}
            value={filters.score_max ?? ""}
            onChange={(e) => setFilters((f) => ({ ...f, score_max: e.target.value ? Number(e.target.value) : undefined }))}
          />
        </div>
        <Button size="sm" onClick={handleApply} className="ml-auto">
          <Search className="h-3.5 w-3.5 mr-1.5" />
          Search
        </Button>
      </div>

      {data.mandate_name && (
        <div className="flex items-center gap-2 mb-4">
          <Clock className="h-3.5 w-3.5 text-neutral-400" />
          <p className="text-sm text-neutral-500">
            Matching against mandate:{" "}
            <span className="font-semibold text-neutral-700">{data.mandate_name}</span>
            <span className="ml-2 text-neutral-400">— {data.total} opportunities found</span>
          </p>
        </div>
      )}

      {isLoading ? (
        <div className="flex h-64 items-center justify-center">
          <LoadingSpinner />
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {data.items.map((deal) => (
            <DiscoveryCard
              key={deal.project_id}
              deal={deal}
              isSelected={selectedIds.includes(deal.project_id)}
              onToggleCompare={() => onToggleCompare(deal.project_id)}
            />
          ))}
        </div>
      )}
    </div>
  );
}

// ── Compare tab ────────────────────────────────────────────────────────────

function CompareTab({ selectedIds, onClear }: { selectedIds: string[]; onClear: () => void }) {
  const compare = useCompareProjects();

  const handleCompare = () => {
    if (selectedIds.length >= 2) compare.mutate(selectedIds);
  };

  const result: CompareResponse = compare.data ?? MOCK_COMPARE_RESULT;

  return (
    <div>
      <div className="flex items-center gap-4 mb-6">
        <p className="text-sm text-neutral-600">
          {selectedIds.length === 0
            ? "Select 2–5 projects from the Discover tab to compare."
            : `${selectedIds.length} project${selectedIds.length > 1 ? "s" : ""} selected`}
        </p>
        {selectedIds.length >= 2 && (
          <Button onClick={handleCompare} disabled={compare.isPending}>
            {compare.isPending ? "Comparing..." : `Compare ${selectedIds.length} Projects`}
          </Button>
        )}
        {selectedIds.length > 0 && (
          <Button variant="outline" onClick={onClear}>Clear Selection</Button>
        )}
      </div>

      <div className="overflow-x-auto rounded-xl border border-neutral-200">
        <table className="w-full text-sm border-collapse">
          <thead>
            <tr className="bg-neutral-50">
              <th className="text-left p-3.5 border-b border-neutral-200 font-semibold text-neutral-600 w-44 text-xs uppercase tracking-wide">
                Dimension
              </th>
              {result.project_names.map((name, i) => (
                <th key={i} className="text-left p-3.5 border-b border-neutral-200 font-semibold text-neutral-700">
                  {name}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {result.rows.map((row, ri) => (
              <tr key={row.dimension} className={`hover:bg-neutral-50 ${ri % 2 === 0 ? "" : "bg-neutral-50/40"}`}>
                <td className="p-3.5 border-b border-neutral-100 text-xs font-semibold text-neutral-500 uppercase tracking-wide">
                  {row.dimension}
                </td>
                {row.values.map((val, i) => {
                  const isBest = row.best_index === i;
                  const isWorst = row.worst_index === i;
                  return (
                    <td
                      key={i}
                      className={`p-3.5 border-b border-neutral-100 font-medium ${
                        isBest
                          ? "bg-green-50 text-green-800"
                          : isWorst
                            ? "bg-red-50 text-red-700"
                            : "text-neutral-700"
                      }`}
                    >
                      <div className="flex items-center gap-1.5">
                        {isBest && <span className="h-1.5 w-1.5 rounded-full bg-green-500 inline-block" />}
                        {isWorst && <span className="h-1.5 w-1.5 rounded-full bg-red-400 inline-block" />}
                        {val == null ? <span className="text-neutral-300">—</span> : String(val)}
                      </div>
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────

export default function DealsPage() {
  const [selectedForCompare, setSelectedForCompare] = useState<string[]>([]);

  const toggleCompare = (id: string) => {
    setSelectedForCompare((prev) =>
      prev.includes(id)
        ? prev.filter((x) => x !== id)
        : prev.length < 5
          ? [...prev, id]
          : prev
    );
  };

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-neutral-900">Deal Intelligence</h1>
          <p className="text-neutral-500 mt-1 text-sm">
            Source, screen, and analyse investment opportunities across your mandate
          </p>
        </div>
      </div>

      <InfoBanner>
        <strong>Deal Pipeline</strong> organises your deal flow across five stages from discovery through negotiation. Track every opportunity, compare projects side by side, and generate screening reports to make faster, better-informed investment decisions.
      </InfoBanner>

      <Tabs defaultValue="pipeline">
        <TabsList>
          <TabsTrigger value="pipeline">
            <Target className="h-3.5 w-3.5 mr-1.5" />
            Pipeline
          </TabsTrigger>
          <TabsTrigger value="discover">
            <Search className="h-3.5 w-3.5 mr-1.5" />
            Discover
          </TabsTrigger>
          <TabsTrigger value="compare">
            Compare
            {selectedForCompare.length > 0 && (
              <Badge variant="neutral" className="ml-2">
                {selectedForCompare.length}
              </Badge>
            )}
          </TabsTrigger>
        </TabsList>

        <TabsContent value="pipeline" className="mt-6">
          <PipelineTab />
        </TabsContent>

        <TabsContent value="discover" className="mt-6">
          <DiscoverTab selectedIds={selectedForCompare} onToggleCompare={toggleCompare} />
        </TabsContent>

        <TabsContent value="compare" className="mt-6">
          <CompareTab selectedIds={selectedForCompare} onClear={() => setSelectedForCompare([])} />
        </TabsContent>
      </Tabs>
    </div>
  );
}
