"use client";

import { useState } from "react";
import {
  Globe,
  MessageSquare,
  Search,
  SlidersHorizontal,
  Users,
  X,
  ChevronRight,
  Send,
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
  useInvestorRecommendations,
  useUpdateMatchStatus,
  useMatchMessages,
  useSendMessage,
  useExpressInterest,
  useRequestIntro,
  alignmentColor,
  alignmentBarColor,
  statusLabel,
  statusVariant,
  ALIGNMENT_DIMENSIONS,
  PIPELINE_STAGES,
  type RecommendedProject,
  type RecommendParams,
} from "@/lib/matching";
import { formatCurrency } from "@/lib/projects";

// ── Constants ─────────────────────────────────────────────────────────────

const PIPELINE_COLUMNS = [
  { key: "suggested",       label: "Suggested" },
  { key: "viewed",          label: "Viewed" },
  { key: "interested",      label: "Interested" },
  { key: "intro_requested", label: "Intro Requested" },
  { key: "engaged",         label: "Engaged" },
  { key: "passed",          label: "Passed" },
] as const;

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

// ── Alignment bar breakdown ───────────────────────────────────────────────

function AlignmentBreakdown({
  alignment,
}: {
  alignment: RecommendedProject["alignment"];
}) {
  return (
    <div className="space-y-2">
      {ALIGNMENT_DIMENSIONS.map((dim) => {
        const score = alignment[dim.key] as number;
        const pct = Math.round((score / dim.max) * 100);
        return (
          <div key={dim.key}>
            <div className="flex justify-between text-xs mb-0.5">
              <span className="text-neutral-600">{dim.label}</span>
              <span className={`font-semibold ${alignmentColor(pct)}`}>
                {score}/{dim.max}
              </span>
            </div>
            <div className="h-1.5 bg-neutral-100 rounded-full overflow-hidden">
              <div
                className={`h-full rounded-full transition-all ${alignmentBarColor(pct)}`}
                style={{ width: `${pct}%` }}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
}

// ── Messaging thread ──────────────────────────────────────────────────────

function MessagingThread({ matchId }: { matchId: string }) {
  const [draft, setDraft] = useState("");
  const { data } = useMatchMessages(matchId);
  const send = useSendMessage();

  function handleSend() {
    const content = draft.trim();
    if (!content) return;
    send.mutate({ matchId, content });
    setDraft("");
  }

  return (
    <div className="flex flex-col h-full">
      <div className="flex-1 overflow-y-auto space-y-3 mb-3 min-h-[120px] max-h-[280px] pr-1">
        {!data || data.items.length === 0 ? (
          <p className="text-xs text-neutral-400 text-center py-6">
            No messages yet. Start the conversation.
          </p>
        ) : (
          data.items.map((msg) => (
            <div
              key={msg.id}
              className={`flex ${msg.is_system ? "justify-center" : "justify-end"}`}
            >
              {msg.is_system ? (
                <span className="text-xs text-neutral-400 bg-neutral-50 px-3 py-1 rounded-full">
                  {msg.content}
                </span>
              ) : (
                <div className="max-w-[80%] bg-primary-600 text-white text-sm px-3 py-2 rounded-lg rounded-br-sm">
                  {msg.content}
                </div>
              )}
            </div>
          ))
        )}
      </div>

      <div className="flex gap-2">
        <input
          type="text"
          className="flex-1 text-sm border border-neutral-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-primary-500"
          placeholder="Type a message…"
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && handleSend()}
        />
        <Button
          size="sm"
          onClick={handleSend}
          disabled={!draft.trim() || send.isPending}
        >
          <Send className="h-4 w-4" />
        </Button>
      </div>
    </div>
  );
}

// ── Match detail modal ────────────────────────────────────────────────────

function MatchDetailModal({
  project,
  onClose,
}: {
  project: RecommendedProject;
  onClose: () => void;
}) {
  const [tab, setTab] = useState<"overview" | "messages">("overview");
  const expressInterest = useExpressInterest();
  const requestIntro = useRequestIntro();

  const matchId = project.match_id;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-2xl max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex items-start justify-between p-6 border-b border-neutral-100">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1">
              <Badge variant={statusVariant(project.status)}>
                {statusLabel(project.status)}
              </Badge>
              {project.mandate_name && (
                <span className="text-xs text-neutral-500">
                  via {project.mandate_name}
                </span>
              )}
            </div>
            <h2 className="text-lg font-bold text-neutral-900 truncate">
              {project.project_name}
            </h2>
            <div className="flex items-center gap-2 text-sm text-neutral-500 mt-1">
              <Globe className="h-3.5 w-3.5" />
              <span>{project.geography_country}</span>
              <span>·</span>
              <span className="capitalize">{typeLabel(project.project_type)}</span>
              <span>·</span>
              <span className="capitalize">{project.stage.replace("_", " ")}</span>
            </div>
          </div>
          <div className="flex items-center gap-3 ml-4">
            <ScoreGauge score={project.alignment.overall} size={56} />
            <button
              onClick={onClose}
              className="p-1.5 text-neutral-400 hover:text-neutral-700 transition-colors"
            >
              <X className="h-5 w-5" />
            </button>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-neutral-100 px-6">
          {(["overview", "messages"] as const).map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`text-sm py-3 px-1 mr-6 border-b-2 transition-colors capitalize ${
                tab === t
                  ? "border-primary-600 text-primary-700 font-semibold"
                  : "border-transparent text-neutral-500 hover:text-neutral-700"
              }`}
            >
              {t === "messages" ? (
                <span className="flex items-center gap-1.5">
                  <MessageSquare className="h-3.5 w-3.5" />
                  Messages
                </span>
              ) : (
                "Overview"
              )}
            </button>
          ))}
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto p-6">
          {tab === "overview" ? (
            <div className="space-y-6">
              {/* Investment info */}
              <div className="grid grid-cols-2 gap-4">
                <div className="bg-neutral-50 rounded-lg p-4">
                  <p className="text-xs text-neutral-500 mb-1">
                    Investment Required
                  </p>
                  <p className="font-bold text-neutral-900">
                    {formatCurrency(
                      Number(project.total_investment_required),
                      project.currency
                    )}
                  </p>
                </div>
                <div className="bg-neutral-50 rounded-lg p-4">
                  <p className="text-xs text-neutral-500 mb-1">
                    Overall Alignment
                  </p>
                  <p
                    className={`font-bold text-xl ${alignmentColor(
                      project.alignment.overall
                    )}`}
                  >
                    {project.alignment.overall}%
                  </p>
                </div>
              </div>

              {/* Alignment breakdown */}
              <div>
                <h3 className="text-sm font-semibold text-neutral-700 mb-3">
                  Alignment Breakdown
                </h3>
                <AlignmentBreakdown alignment={project.alignment} />
              </div>
            </div>
          ) : (
            <div className="h-full">
              {matchId ? (
                <MessagingThread matchId={matchId} />
              ) : (
                <p className="text-sm text-neutral-500 text-center py-8">
                  Express interest to unlock messaging.
                </p>
              )}
            </div>
          )}
        </div>

        {/* Footer actions */}
        <div className="flex items-center justify-end gap-3 p-6 border-t border-neutral-100">
          {matchId && project.status === "suggested" && (
            <Button
              onClick={() => expressInterest.mutate(matchId)}
              disabled={expressInterest.isPending}
            >
              Express Interest
            </Button>
          )}
          {matchId && project.status === "interested" && (
            <Button
              onClick={() => requestIntro.mutate(matchId)}
              disabled={requestIntro.isPending}
            >
              Request Introduction
            </Button>
          )}
          <Button variant="outline" onClick={onClose}>
            Close
          </Button>
        </div>
      </div>
    </div>
  );
}

// ── Recommendation card ───────────────────────────────────────────────────

function RecommendationCard({
  project,
  onSelect,
}: {
  project: RecommendedProject;
  onSelect: () => void;
}) {
  const gradient = typeGradient(project.project_type);

  return (
    <Card className="overflow-hidden hover:shadow-md transition-shadow cursor-pointer" onClick={onSelect}>
      <div className={`h-20 bg-gradient-to-br ${gradient} relative`}>
        <div className="absolute inset-0 flex items-end p-3">
          <Badge variant="neutral" className="text-xs bg-white/90 text-neutral-700">
            {typeLabel(project.project_type)}
          </Badge>
        </div>
        {project.match_id && (
          <div className="absolute top-2 right-2">
            <Badge variant={statusVariant(project.status)} className="text-xs">
              {statusLabel(project.status)}
            </Badge>
          </div>
        )}
      </div>

      <CardContent className="p-4">
        <div className="flex items-start justify-between gap-2 mb-2">
          <h3 className="font-semibold text-sm leading-tight line-clamp-2 flex-1">
            {project.project_name}
          </h3>
          {project.signal_score != null && (
            <ScoreGauge score={project.signal_score} size={40} />
          )}
        </div>

        <div className="flex items-center gap-2 text-xs text-neutral-500 mb-1">
          <Globe className="h-3 w-3" />
          <span>{project.geography_country}</span>
          <span>·</span>
          <span className="capitalize">{project.stage.replace("_", " ")}</span>
        </div>

        <p className="text-sm font-semibold text-neutral-800 mb-3">
          {formatCurrency(
            Number(project.total_investment_required),
            project.currency
          )}
        </p>

        {/* Overall alignment bar */}
        <div className="mb-3">
          <div className="flex justify-between text-xs mb-1">
            <span className="text-neutral-500">Alignment</span>
            <span
              className={`font-semibold ${alignmentColor(
                project.alignment.overall
              )}`}
            >
              {project.alignment.overall}%
            </span>
          </div>
          <div className="h-1.5 bg-neutral-100 rounded-full overflow-hidden">
            <div
              className={`h-full rounded-full transition-all ${alignmentBarColor(
                project.alignment.overall
              )}`}
              style={{ width: `${project.alignment.overall}%` }}
            />
          </div>
        </div>

        <div className="flex items-center justify-between">
          <span className="text-xs text-neutral-400">
            {project.mandate_name ?? "No mandate matched"}
          </span>
          <ChevronRight className="h-4 w-4 text-neutral-400" />
        </div>
      </CardContent>
    </Card>
  );
}

// ── Recommendations tab ───────────────────────────────────────────────────

function RecommendationsTab({
  onSelectProject,
}: {
  onSelectProject: (p: RecommendedProject) => void;
}) {
  const [params, setParams] = useState<RecommendParams>({
    sort_by: "alignment",
  });
  const [showFilters, setShowFilters] = useState(false);
  const [sector, setSector] = useState("");
  const [geography, setGeography] = useState("");
  const [minAlignment, setMinAlignment] = useState("");

  const { data, isLoading } = useInvestorRecommendations(params);

  function applyFilters() {
    setParams({
      sector: sector || undefined,
      geography: geography || undefined,
      min_alignment: minAlignment ? Number(minAlignment) : undefined,
      sort_by: params.sort_by,
    });
    setShowFilters(false);
  }

  function clearFilters() {
    setSector("");
    setGeography("");
    setMinAlignment("");
    setParams({ sort_by: params.sort_by });
  }

  const hasFilters = !!(params.sector || params.geography || params.min_alignment);

  return (
    <div>
      {/* Toolbar */}
      <div className="flex items-center justify-between gap-3 mb-5">
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setShowFilters((v) => !v)}
          >
            <SlidersHorizontal className="h-4 w-4 mr-1.5" />
            Filters
            {hasFilters && (
              <Badge variant="info" className="ml-2 text-xs">
                Active
              </Badge>
            )}
          </Button>
          {hasFilters && (
            <button
              onClick={clearFilters}
              className="text-xs text-neutral-400 hover:text-neutral-700 transition-colors"
            >
              Clear
            </button>
          )}
        </div>

        <div className="flex items-center gap-2">
          <span className="text-xs text-neutral-500">Sort:</span>
          <select
            className="text-xs border border-neutral-200 rounded px-2 h-8 bg-white"
            value={params.sort_by}
            onChange={(e) =>
              setParams((p) => ({
                ...p,
                sort_by: e.target.value as RecommendParams["sort_by"],
              }))
            }
          >
            <option value="alignment">Alignment</option>
            <option value="signal_score">Signal Score</option>
            <option value="recency">Recency</option>
          </select>
        </div>
      </div>

      {/* Filter panel */}
      {showFilters && (
        <div className="bg-neutral-50 border border-neutral-200 rounded-lg p-4 mb-5 grid grid-cols-3 gap-4">
          <div>
            <label className="block text-xs font-medium text-neutral-600 mb-1">
              Sector
            </label>
            <input
              type="text"
              className="w-full text-sm border border-neutral-200 rounded px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-primary-500"
              placeholder="e.g. solar"
              value={sector}
              onChange={(e) => setSector(e.target.value)}
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-neutral-600 mb-1">
              Geography
            </label>
            <input
              type="text"
              className="w-full text-sm border border-neutral-200 rounded px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-primary-500"
              placeholder="e.g. Kenya"
              value={geography}
              onChange={(e) => setGeography(e.target.value)}
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-neutral-600 mb-1">
              Min. Alignment %
            </label>
            <input
              type="number"
              min={0}
              max={100}
              className="w-full text-sm border border-neutral-200 rounded px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-primary-500"
              placeholder="e.g. 60"
              value={minAlignment}
              onChange={(e) => setMinAlignment(e.target.value)}
            />
          </div>
          <div className="col-span-3 flex justify-end gap-2">
            <Button variant="outline" size="sm" onClick={() => setShowFilters(false)}>
              Cancel
            </Button>
            <Button size="sm" onClick={applyFilters}>
              Apply Filters
            </Button>
          </div>
        </div>
      )}

      {/* Results */}
      {isLoading ? (
        <div className="flex h-64 items-center justify-center">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary-600 border-t-transparent" />
        </div>
      ) : !data || data.items.length === 0 ? (
        <EmptyState
          icon={<Search className="h-8 w-8" />}
          title="No recommendations yet"
          description="Set up investment mandates to receive matched project recommendations."
        />
      ) : (
        <>
          <p className="text-xs text-neutral-500 mb-4">
            {data.total} project{data.total !== 1 ? "s" : ""} matched your criteria
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {data.items.map((project) => (
              <RecommendationCard
                key={project.project_id}
                project={project}
                onSelect={() => onSelectProject(project)}
              />
            ))}
          </div>
        </>
      )}
    </div>
  );
}

// ── Pipeline tab ──────────────────────────────────────────────────────────

function PipelineCard({
  project,
  onSelect,
}: {
  project: RecommendedProject;
  onSelect: () => void;
}) {
  const updateStatus = useUpdateMatchStatus();

  return (
    <Card className="mb-3 cursor-pointer hover:shadow-md transition-shadow">
      <CardContent className="p-3">
        <div
          className="flex items-start justify-between gap-2 mb-2"
          onClick={onSelect}
        >
          <p className="font-medium text-sm leading-tight line-clamp-2 flex-1">
            {project.project_name}
          </p>
          {project.signal_score != null && (
            <ScoreGauge score={project.signal_score} size={36} />
          )}
        </div>

        <div className="flex items-center gap-1 text-xs text-neutral-500 mb-2">
          <Globe className="h-3 w-3" />
          <span>{project.geography_country}</span>
          <span>·</span>
          <span className="capitalize">{typeLabel(project.project_type)}</span>
        </div>

        <div className="flex items-center justify-between mb-2">
          <span
            className={`text-xs font-semibold ${alignmentColor(
              project.alignment.overall
            )}`}
          >
            {project.alignment.overall}% aligned
          </span>
          {project.updated_at && (
            <span className="text-xs text-neutral-400">
              {new Date(project.updated_at).toLocaleDateString()}
            </span>
          )}
        </div>

        <div className="flex gap-2">
          <Button
            size="sm"
            variant="outline"
            className="flex-1 text-xs h-7"
            onClick={onSelect}
          >
            View
            <ChevronRight className="h-3 w-3 ml-1" />
          </Button>
          {project.match_id && (
            <select
              className="text-xs border border-neutral-200 rounded px-1 h-7 bg-white text-neutral-700"
              value={project.status}
              onClick={(e) => e.stopPropagation()}
              onChange={(e) => {
                if (!project.match_id) return;
                updateStatus.mutate({
                  matchId: project.match_id,
                  status: e.target.value,
                });
              }}
            >
              {PIPELINE_STAGES.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

function PipelineTab({
  onSelectProject,
}: {
  onSelectProject: (p: RecommendedProject) => void;
}) {
  const { data, isLoading } = useInvestorRecommendations();

  if (isLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary-600 border-t-transparent" />
      </div>
    );
  }

  if (!data || data.items.length === 0) {
    return (
      <EmptyState
        icon={<Users className="h-8 w-8" />}
        title="Pipeline is empty"
        description="Projects you interact with will appear in your pipeline."
      />
    );
  }

  // Group by status
  const grouped: Record<string, RecommendedProject[]> = {};
  for (const col of PIPELINE_COLUMNS) {
    grouped[col.key] = [];
  }
  for (const p of data.items) {
    if (p.status in grouped) {
      grouped[p.status].push(p);
    }
  }

  return (
    <div className="overflow-x-auto">
      <div className="flex gap-4 min-w-[960px] pb-4">
        {PIPELINE_COLUMNS.map((col) => {
          const cards = grouped[col.key] ?? [];
          return (
            <div key={col.key} className="flex-1 min-w-[160px]">
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
                  cards.map((p) => (
                    <PipelineCard
                      key={p.project_id}
                      project={p}
                      onSelect={() => onSelectProject(p)}
                    />
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

// ── Page ──────────────────────────────────────────────────────────────────

export default function MatchingPage() {
  const [selectedProject, setSelectedProject] =
    useState<RecommendedProject | null>(null);

  return (
    <div className="p-6 max-w-screen-xl mx-auto">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-neutral-900">
          Investor Matching
        </h1>
        <p className="text-sm text-neutral-500 mt-1">
          AI-scored project recommendations matched to your investment mandates.
        </p>
      </div>

      <Tabs defaultValue="recommendations">
        <TabsList className="mb-6">
          <TabsTrigger value="recommendations">Recommendations</TabsTrigger>
          <TabsTrigger value="pipeline">My Pipeline</TabsTrigger>
        </TabsList>

        <TabsContent value="recommendations">
          <RecommendationsTab onSelectProject={setSelectedProject} />
        </TabsContent>

        <TabsContent value="pipeline">
          <PipelineTab onSelectProject={setSelectedProject} />
        </TabsContent>
      </Tabs>

      {/* Match detail modal */}
      {selectedProject && (
        <MatchDetailModal
          project={selectedProject}
          onClose={() => setSelectedProject(null)}
        />
      )}
    </div>
  );
}
