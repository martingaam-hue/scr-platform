"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import {
  Globe,
  MapPin,
  Search,
  SlidersHorizontal,
  TrendingUp,
  Zap,
  CheckSquare,
  Square,
  ChevronRight,
} from "lucide-react";
import {
  Badge,
  Button,
  Card,
  CardContent,
  EmptyState,
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
  alignmentBgColor,
  PIPELINE_STATUS_OPTIONS,
  type DealCard,
  type DiscoveryDeal,
  type CompareResponse,
  type DiscoverParams,
} from "@/lib/deals";
import { formatCurrency } from "@/lib/projects";

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
  const { data, isLoading } = useDealPipeline();

  if (isLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary-600 border-t-transparent" />
      </div>
    );
  }

  if (!data) return null;

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

  const { data, isLoading } = useDiscoverDeals(applied);

  const handleApply = () => setApplied({ ...filters });

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

      {data?.mandate_name && (
        <p className="text-sm text-neutral-500 mb-4">
          Matching against mandate:{" "}
          <span className="font-medium">{data.mandate_name}</span>
        </p>
      )}

      {isLoading ? (
        <div className="flex h-64 items-center justify-center">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary-600 border-t-transparent" />
        </div>
      ) : !data || data.items.length === 0 ? (
        <EmptyState
          icon={<TrendingUp className="h-12 w-12 text-neutral-400" />}
          title="No deals found"
          description={
            !data?.mandate_name
              ? "Set up an investor mandate to start discovering deals."
              : "No published projects match your current filters."
          }
        />
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

  const result: CompareResponse | undefined = compare.data;

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

      {result && (
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
      )}
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
