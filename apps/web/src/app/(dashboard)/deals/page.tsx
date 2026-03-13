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
} from "lucide-react";
import {
  Badge,
  Button,
  Card,
  CardContent,
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
import { InfoBanner } from "@/components/info-banner";

// ── Mock data ─────────────────────────────────────────────────────────────

// Pipeline mock — 5 canonical pipeline deals
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
  ] as DealCard[],
  passed: [] as DealCard[],
};

// Discovery mock — 5 new deals not yet in pipeline
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
  ] as DiscoveryDeal[],
  total: 5,
  mandate_name: "European Renewables Fund Mandate",
};

// Compare mock — p2/p3/p4 side by side
const MOCK_COMPARE_RESULT: CompareResponse = {
  project_ids: ["p2", "p3", "p4"],
  project_names: ["Danube Hydro Expansion", "Aegean Wind Cluster", "Bavarian Biomass Network"],
  rows: [
    { dimension: "Signal Score",    values: [72, 69, 76],        best_index: 2, worst_index: 1 },
    { dimension: "IRR (%)",         values: ["11.8%", "10.4%", "12.1%"], best_index: 2, worst_index: 1 },
    { dimension: "Target Size",     values: ["€28M", "€42M", "€15M"],   best_index: null, worst_index: null },
    { dimension: "Sector",          values: ["Hydro", "Wind", "Biomass"], best_index: null, worst_index: null },
    { dimension: "Geography",       values: ["Romania", "Greece", "Germany"], best_index: 2, worst_index: null },
    { dimension: "Stage",           values: ["Due Diligence", "Due Diligence", "Negotiation"], best_index: 2, worst_index: null },
    { dimension: "Alignment Score", values: [75, 71, 80],        best_index: 2, worst_index: 1 },
    { dimension: "Risk Score",      values: [68, 65, 72],        best_index: 2, worst_index: 1 },
  ],
};

// ── Project type icons ────────────────────────────────────────────────────

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

function typeGradient(type: string): string {
  return TYPE_COLORS[type] ?? TYPE_COLORS.other;
}

function typeLabel(type: string): string {
  return type
    .split("_")
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");
}

// ── Pipeline column ───────────────────────────────────────────────────────

const PIPELINE_COLUMNS = [
  { key: "discovered", label: "Discovered" },
  { key: "screening", label: "Screening" },
  { key: "due_diligence", label: "Due Diligence" },
  { key: "negotiation", label: "Negotiation" },
  { key: "passed", label: "Passed" },
] as const;

function PipelineCard({ card }: { card: DealCard }) {
  const router = useRouter();
  const updateStatus = useUpdateDealStatus();

  return (
    <Card className="mb-3 cursor-pointer hover:shadow-md transition-shadow">
      <CardContent className="p-3">
        <div className="flex items-start justify-between gap-2 mb-2">
          <p
            className="font-medium text-sm leading-tight line-clamp-2 flex-1"
            onClick={() => router.push(`/deals/${card.project_id}`)}
          >
            {card.project_name}
          </p>
          {card.signal_score != null && (
            <ScoreGauge score={card.signal_score} size={40} />
          )}
        </div>

        <div className="flex items-center gap-1 text-xs text-neutral-500 mb-1">
          <Globe className="h-3 w-3" />
          <span>{card.geography_country}</span>
        </div>
        <div className="flex items-center gap-1 text-xs text-neutral-500 mb-2">
          <span className="capitalize">{typeLabel(card.project_type)}</span>
          <span>·</span>
          <span className="capitalize">{card.stage.replace("_", " ")}</span>
        </div>

        <div className="flex items-center justify-between mb-3">
          <span className={`text-xs font-semibold ${alignmentColor(card.alignment_score)}`}>
            {card.alignment_score}% aligned
          </span>
          <span className="text-xs text-neutral-400">
            {new Date(card.updated_at).toLocaleDateString()}
          </span>
        </div>

        <div className="flex gap-2">
          <Button
            size="sm"
            variant="outline"
            className="flex-1 text-xs h-7"
            onClick={() => router.push(`/deals/${card.project_id}`)}
          >
            Screen
            <ChevronRight className="h-3 w-3 ml-1" />
          </Button>
          <select
            className="text-xs border border-neutral-200 rounded px-1 h-7 bg-white text-neutral-700"
            value={card.status}
            onChange={(e) =>
              updateStatus.mutate({
                projectId: card.project_id,
                status: e.target.value,
              })
            }
          >
            {PIPELINE_STATUS_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>
      </CardContent>
    </Card>
  );
}

function PipelineTab() {
  const { data: apiData, isLoading } = useDealPipeline();

  if (isLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary-600 border-t-transparent" />
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

  return (
    <div className="overflow-x-auto">
      <div className="flex gap-4 min-w-[900px] pb-4">
        {PIPELINE_COLUMNS.map((col) => {
          const cards = columnData[col.key] ?? [];
          return (
            <div key={col.key} className="flex-1 min-w-[180px]">
              <div className="flex items-center justify-between mb-3">
                <h3 className="font-semibold text-sm text-neutral-700">
                  {col.label}
                </h3>
                <Badge variant="neutral">{cards.length}</Badge>
              </div>
              <div className="min-h-[200px]">
                {cards.length === 0 ? (
                  <p className="text-xs text-neutral-400 text-center mt-8">
                    No deals
                  </p>
                ) : (
                  cards.map((card) => (
                    <PipelineCard key={card.match_id} card={card} />
                  ))
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ── Discovery tab ─────────────────────────────────────────────────────────

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
      <div className={`h-24 bg-gradient-to-br ${gradient} relative`}>
        <div className="absolute inset-0 flex items-end p-3">
          <Badge variant="neutral" className="text-xs bg-white/90 text-neutral-700">
            {typeLabel(deal.project_type)}
          </Badge>
        </div>
      </div>

      <CardContent className="p-4">
        <div className="flex items-start justify-between gap-2 mb-2">
          <h3 className="font-semibold text-sm leading-tight line-clamp-2 flex-1">
            {deal.project_name}
          </h3>
          {deal.signal_score != null && (
            <ScoreGauge score={deal.signal_score} size={44} />
          )}
        </div>

        <div className="flex items-center gap-2 text-xs text-neutral-500 mb-1">
          <Globe className="h-3 w-3" />
          <span>{deal.geography_country}</span>
          <span>·</span>
          <span className="capitalize">{deal.stage.replace("_", " ")}</span>
        </div>

        <p className="text-sm font-semibold text-neutral-800 mb-3">
          {formatCurrency(Number(deal.total_investment_required), deal.currency)}
        </p>

        {/* Alignment bar */}
        <div className="mb-3">
          <div className="flex justify-between text-xs mb-1">
            <span className="text-neutral-500">Alignment</span>
            <span className={`font-semibold ${alignmentColor(deal.alignment_score)}`}>
              {deal.alignment_score}%
            </span>
          </div>
          <div className="h-1.5 bg-neutral-100 rounded-full overflow-hidden">
            <div
              className={`h-full rounded-full transition-all ${
                deal.alignment_score >= 70
                  ? "bg-green-500"
                  : deal.alignment_score >= 40
                    ? "bg-amber-500"
                    : "bg-red-400"
              }`}
              style={{ width: `${deal.alignment_score}%` }}
            />
          </div>
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
            Screen
          </Button>
          {!deal.is_in_pipeline && (
            <Button
              size="sm"
              className="text-xs h-7"
              onClick={() =>
                updateStatus.mutate({
                  projectId: deal.project_id,
                  status: "suggested",
                })
              }
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
      <div className="flex flex-wrap gap-3 mb-6 p-4 bg-neutral-50 rounded-lg border border-neutral-200">
        <div className="flex items-center gap-2">
          <SlidersHorizontal className="h-4 w-4 text-neutral-500" />
          <span className="text-sm font-medium text-neutral-600">Filters</span>
        </div>
        <select
          className="text-sm border border-neutral-200 rounded px-2 py-1 bg-white"
          value={filters.sector ?? ""}
          onChange={(e) =>
            setFilters((f) => ({ ...f, sector: e.target.value || undefined }))
          }
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
          className="text-sm border border-neutral-200 rounded px-2 py-1 w-36"
          value={filters.geography ?? ""}
          onChange={(e) =>
            setFilters((f) => ({
              ...f,
              geography: e.target.value || undefined,
            }))
          }
        />
        <div className="flex items-center gap-1">
          <input
            type="number"
            placeholder="Score min"
            className="text-sm border border-neutral-200 rounded px-2 py-1 w-24"
            min={0}
            max={100}
            value={filters.score_min ?? ""}
            onChange={(e) =>
              setFilters((f) => ({
                ...f,
                score_min: e.target.value ? Number(e.target.value) : undefined,
              }))
            }
          />
          <span className="text-neutral-400">–</span>
          <input
            type="number"
            placeholder="Score max"
            className="text-sm border border-neutral-200 rounded px-2 py-1 w-24"
            min={0}
            max={100}
            value={filters.score_max ?? ""}
            onChange={(e) =>
              setFilters((f) => ({
                ...f,
                score_max: e.target.value ? Number(e.target.value) : undefined,
              }))
            }
          />
        </div>
        <Button size="sm" onClick={handleApply}>
          <Search className="h-3.5 w-3.5 mr-1" />
          Apply
        </Button>
      </div>

      {data.mandate_name && (
        <p className="text-sm text-neutral-500 mb-4">
          Matching against mandate:{" "}
          <span className="font-medium">{data.mandate_name}</span>
        </p>
      )}

      {isLoading ? (
        <div className="flex h-64 items-center justify-center">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary-600 border-t-transparent" />
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

// ── Compare tab ───────────────────────────────────────────────────────────

function CompareTab({ selectedIds, onClear }: { selectedIds: string[]; onClear: () => void }) {
  const compare = useCompareProjects();

  const handleCompare = () => {
    if (selectedIds.length >= 2) {
      compare.mutate(selectedIds);
    }
  };

  // Fall back to mock compare result when no user comparison has been run
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
          <Button variant="outline" onClick={onClear}>
            Clear Selection
          </Button>
        )}
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-sm border-collapse">
            <thead>
              <tr>
                <th className="text-left p-3 bg-neutral-50 border border-neutral-200 font-semibold text-neutral-700 w-40">
                  Dimension
                </th>
                {result.project_names.map((name, i) => (
                  <th
                    key={i}
                    className="text-left p-3 bg-neutral-50 border border-neutral-200 font-semibold text-neutral-700"
                  >
                    {name}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {result.rows.map((row) => (
                <tr key={row.dimension} className="hover:bg-neutral-50">
                  <td className="p-3 border border-neutral-200 font-medium text-neutral-600">
                    {row.dimension}
                  </td>
                  {row.values.map((val, i) => {
                    const isBest = row.best_index === i;
                    const isWorst = row.worst_index === i;
                    return (
                      <td
                        key={i}
                        className={`p-3 border border-neutral-200 ${
                          isBest
                            ? "bg-green-50 border-green-200 font-semibold text-green-800"
                            : isWorst
                              ? "bg-red-50 border-red-200 text-red-700"
                              : ""
                        }`}
                      >
                        {val == null ? (
                          <span className="text-neutral-300">—</span>
                        ) : (
                          String(val)
                        )}
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
      <div>
        <h1 className="text-2xl font-bold text-neutral-900">Deal Intelligence</h1>
        <p className="text-neutral-500 mt-1">
          AI-powered deal sourcing, screening, and analysis
        </p>
      </div>

      <InfoBanner>
        <strong>Deal Pipeline</strong> organizes your deal flow across five stages from discovery through negotiation. Track every opportunity, compare projects side by side, and generate AI screening reports to make faster, better-informed investment decisions.
      </InfoBanner>

      <Tabs defaultValue="pipeline">
        <TabsList>
          <TabsTrigger value="pipeline">Pipeline</TabsTrigger>
          <TabsTrigger value="discover">Discover</TabsTrigger>
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
          <DiscoverTab
            selectedIds={selectedForCompare}
            onToggleCompare={toggleCompare}
          />
        </TabsContent>

        <TabsContent value="compare" className="mt-6">
          <CompareTab
            selectedIds={selectedForCompare}
            onClear={() => setSelectedForCompare([])}
          />
        </TabsContent>
      </Tabs>
    </div>
  );
}
