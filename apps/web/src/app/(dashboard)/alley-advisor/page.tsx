"use client";

import { useState } from "react";
import {
  Loader2,
  Brain,
  CheckCircle2,
  AlertCircle,
  Send,
  Clock,
} from "lucide-react";
import {
  Badge,
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  Tabs,
  TabsList,
  TabsTrigger,
  TabsContent,
  cn,
} from "@scr/ui";
import { useAlleyScores } from "@/lib/alley-score";
import {
  useAdvisorQuery,
  useFinancingReadiness,
  useMarketPositioning,
  useMilestonePlan,
  useRegulatoryGuidance,
  milestoneStatusVariant,
} from "@/lib/alley-advisor";

// ── Helpers ──────────────────────────────────────────────────────────────────

function SectionEmpty({ message }: { message: string }) {
  return (
    <div className="flex flex-col items-center justify-center py-12 text-center">
      <Brain className="h-8 w-8 text-neutral-300 mb-2" />
      <p className="text-sm text-neutral-400 max-w-xs">{message}</p>
    </div>
  );
}

function ListItems({
  title,
  items,
  icon,
  itemColor,
}: {
  title: string;
  items: string[];
  icon: React.ReactNode;
  itemColor?: string;
}) {
  if (!items.length) return null;
  return (
    <div>
      <h4 className="text-xs font-semibold text-neutral-500 uppercase tracking-wide mb-2">
        {title}
      </h4>
      <ul className="space-y-1">
        {items.map((item, i) => (
          <li key={i} className="flex items-start gap-2 text-sm">
            <span className={cn("mt-0.5 shrink-0", itemColor)}>{icon}</span>
            <span className="text-neutral-700">{item}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

// ── Financing Readiness Tab ───────────────────────────────────────────────────

function FinancingTab({ projectId }: { projectId: string }) {
  const { data, isLoading } = useFinancingReadiness(projectId);

  if (isLoading) {
    return (
      <div className="flex justify-center py-16">
        <Loader2 className="h-6 w-6 animate-spin text-neutral-400" />
      </div>
    );
  }
  if (!data) {
    return (
      <SectionEmpty message="Financing readiness analysis will appear here once generated." />
    );
  }

  const gaugeColor =
    data.readiness_score >= 70
      ? "text-green-600"
      : data.readiness_score >= 40
      ? "text-amber-600"
      : "text-red-600";

  return (
    <div className="space-y-6">
      {/* Gauge */}
      <Card>
        <CardContent className="pt-5 pb-4 flex items-center gap-6">
          <div className="flex flex-col items-center shrink-0">
            <span className={cn("text-5xl font-bold tabular-nums", gaugeColor)}>
              {data.readiness_score}
            </span>
            <span className="text-xs text-neutral-400 mt-1">/ 100</span>
          </div>
          <div>
            <p className="text-lg font-semibold text-neutral-800">
              {data.readiness_label}
            </p>
            <p className="text-xs text-neutral-400 mt-0.5">Financing Readiness Score</p>
            <div className="mt-2 h-2 w-48 bg-neutral-100 rounded-full overflow-hidden">
              <div
                className={cn(
                  "h-full rounded-full",
                  data.readiness_score >= 70
                    ? "bg-green-500"
                    : data.readiness_score >= 40
                    ? "bg-amber-500"
                    : "bg-red-500"
                )}
                style={{ width: `${data.readiness_score}%` }}
              />
            </div>
          </div>
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 gap-5 sm:grid-cols-2">
        {/* Strengths & gaps */}
        <Card>
          <CardContent className="pt-4 space-y-4">
            <ListItems
              title="Strengths"
              items={data.strengths}
              icon={<CheckCircle2 className="h-3.5 w-3.5" />}
              itemColor="text-green-500"
            />
            <ListItems
              title="Gaps"
              items={data.gaps}
              icon={<AlertCircle className="h-3.5 w-3.5" />}
              itemColor="text-red-500"
            />
          </CardContent>
        </Card>

        {/* Instruments & next steps */}
        <Card>
          <CardContent className="pt-4 space-y-4">
            <div>
              <h4 className="text-xs font-semibold text-neutral-500 uppercase tracking-wide mb-2">
                Recommended Instruments
              </h4>
              <div className="flex flex-wrap gap-1.5">
                {data.recommended_instruments.map((inst) => (
                  <Badge key={inst} variant="neutral">
                    {inst}
                  </Badge>
                ))}
              </div>
            </div>
            <ListItems
              title="Next Steps"
              items={data.next_steps}
              icon={<CheckCircle2 className="h-3.5 w-3.5" />}
              itemColor="text-blue-500"
            />
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

// ── Market Positioning Tab ────────────────────────────────────────────────────

function PositioningTab({ projectId }: { projectId: string }) {
  const { data, isLoading } = useMarketPositioning(projectId);

  if (isLoading) {
    return (
      <div className="flex justify-center py-16">
        <Loader2 className="h-6 w-6 animate-spin text-neutral-400" />
      </div>
    );
  }
  if (!data) {
    return (
      <SectionEmpty message="Market positioning analysis will appear here once generated." />
    );
  }

  return (
    <div className="space-y-5">
      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Positioning Summary</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-neutral-700 leading-relaxed">
            {data.positioning_summary}
          </p>
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 gap-5 sm:grid-cols-2">
        <Card>
          <CardContent className="pt-4 space-y-4">
            <ListItems
              title="Competitive Advantages"
              items={data.competitive_advantages}
              icon={<CheckCircle2 className="h-3.5 w-3.5" />}
              itemColor="text-green-500"
            />
            <ListItems
              title="Market Risks"
              items={data.market_risks}
              icon={<AlertCircle className="h-3.5 w-3.5" />}
              itemColor="text-red-500"
            />
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-4">
            <h4 className="text-xs font-semibold text-neutral-500 uppercase tracking-wide mb-2">
              Target Investor Profiles
            </h4>
            <div className="space-y-1.5">
              {data.target_investor_profiles.map((profile) => (
                <div
                  key={profile}
                  className="text-sm bg-blue-50 text-blue-700 rounded px-3 py-1.5"
                >
                  {profile}
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

// ── Milestone Plan Tab ────────────────────────────────────────────────────────

function MilestonesTab({ projectId }: { projectId: string }) {
  const { data, isLoading } = useMilestonePlan(projectId);

  if (isLoading) {
    return (
      <div className="flex justify-center py-16">
        <Loader2 className="h-6 w-6 animate-spin text-neutral-400" />
      </div>
    );
  }
  if (!data?.milestones?.length) {
    return (
      <SectionEmpty message="Milestone plan will appear here once generated." />
    );
  }

  return (
    <div className="space-y-3">
      {data.milestones.map((ms, i) => (
        <Card key={i}>
          <CardContent className="pt-4 pb-4">
            <div className="flex items-start gap-4">
              <div className="shrink-0 flex flex-col items-center gap-1">
                <div className="h-7 w-7 rounded-full bg-blue-100 text-blue-700 text-xs font-bold flex items-center justify-center">
                  {i + 1}
                </div>
                <div className="flex items-center gap-1 text-xs text-neutral-400">
                  <Clock className="h-3 w-3" />
                  {ms.target_months}mo
                </div>
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 flex-wrap mb-1">
                  <span className="font-semibold text-sm text-neutral-800">
                    {ms.title}
                  </span>
                  <Badge variant={milestoneStatusVariant(ms.status)}>
                    {ms.status.replace("_", " ")}
                  </Badge>
                </div>
                <p className="text-xs text-neutral-500">{ms.description}</p>
                {ms.dependencies.length > 0 && (
                  <div className="flex flex-wrap gap-1 mt-2">
                    <span className="text-xs text-neutral-400">Deps:</span>
                    {ms.dependencies.map((dep) => (
                      <span
                        key={dep}
                        className="text-xs bg-neutral-100 text-neutral-600 px-1.5 py-0.5 rounded"
                      >
                        {dep}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

// ── Regulatory Guidance Tab ───────────────────────────────────────────────────

function RegulatoryTab({ projectId }: { projectId: string }) {
  const { data, isLoading } = useRegulatoryGuidance(projectId);

  if (isLoading) {
    return (
      <div className="flex justify-center py-16">
        <Loader2 className="h-6 w-6 animate-spin text-neutral-400" />
      </div>
    );
  }
  if (!data) {
    return (
      <SectionEmpty message="Regulatory guidance will appear here once generated." />
    );
  }

  return (
    <div className="space-y-5">
      {/* Header meta */}
      <div className="flex items-center gap-4 flex-wrap text-sm">
        <Badge variant="neutral">{data.jurisdiction}</Badge>
        <span className="text-neutral-500">
          Timeline estimate:{" "}
          <strong className="text-neutral-700">{data.timeline_estimate}</strong>
        </span>
      </div>

      <div className="grid grid-cols-1 gap-5 sm:grid-cols-2">
        <Card>
          <CardContent className="pt-4 space-y-4">
            <div>
              <h4 className="text-xs font-semibold text-neutral-500 uppercase tracking-wide mb-2">
                Key Requirements
              </h4>
              <ul className="space-y-1.5">
                {data.key_requirements.map((req, i) => (
                  <li key={i} className="flex items-start gap-2 text-sm">
                    <input
                      type="checkbox"
                      readOnly
                      className="mt-0.5 shrink-0"
                    />
                    <span className="text-neutral-700">{req}</span>
                  </li>
                ))}
              </ul>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-4 space-y-4">
            <div>
              <h4 className="text-xs font-semibold text-neutral-500 uppercase tracking-wide mb-2">
                Approvals Needed
              </h4>
              <div className="space-y-1">
                {data.approvals_needed.map((a) => (
                  <div
                    key={a}
                    className="text-sm bg-amber-50 text-amber-700 rounded px-3 py-1.5"
                  >
                    {a}
                  </div>
                ))}
              </div>
            </div>
            <ListItems
              title="Risk Areas"
              items={data.risk_areas}
              icon={<AlertCircle className="h-3.5 w-3.5" />}
              itemColor="text-red-500"
            />
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

// ── Free-Form Query Box ───────────────────────────────────────────────────────

function AdvisorQueryBox({ projectId }: { projectId: string }) {
  const [query, setQuery] = useState("");
  const [response, setResponse] = useState<string | null>(null);
  const advisorQuery = useAdvisorQuery();

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!query.trim()) return;
    const result = await advisorQuery.mutateAsync({ id: projectId, query });
    setResponse(result.response);
    setQuery("");
  }

  return (
    <Card className="border-blue-100">
      <CardHeader className="pb-2">
        <CardTitle className="text-sm">Ask the Advisor</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {response && (
          <div className="bg-blue-50 border border-blue-100 rounded-lg px-4 py-3 text-sm text-blue-900 leading-relaxed whitespace-pre-wrap">
            {response}
          </div>
        )}
        <form onSubmit={handleSubmit} className="flex gap-2">
          <input
            type="text"
            placeholder="Ask a strategic question about your project..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="flex-1 text-sm border border-neutral-200 rounded px-3 py-2 bg-white focus:outline-none focus:ring-1 focus:ring-blue-400"
          />
          <Button
            type="submit"
            size="sm"
            disabled={advisorQuery.isPending || !query.trim()}
          >
            {advisorQuery.isPending ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Send className="h-4 w-4" />
            )}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}

// ── Page ─────────────────────────────────────────────────────────────────────

export default function AlleyAdvisorPage() {
  const { data: scoresData, isLoading: loadingProjects } = useAlleyScores();
  const [selectedProjectId, setSelectedProjectId] = useState<string>("");

  const projects = scoresData?.projects ?? [];

  // Auto-select first project
  const effectiveProjectId =
    selectedProjectId || projects[0]?.project_id || "";

  return (
    <div className="max-w-5xl mx-auto px-4 py-8 space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <Brain className="h-6 w-6 text-purple-600" />
        <div>
          <h1 className="text-xl font-bold text-neutral-900">
            Development Advisor
          </h1>
          <p className="text-sm text-neutral-500">
            AI-powered strategic guidance for your projects
          </p>
        </div>
      </div>

      {/* Project selector */}
      <Card>
        <CardContent className="pt-4 pb-4">
          <div className="flex items-center gap-3">
            <label className="text-sm font-medium text-neutral-700 shrink-0">
              Project:
            </label>
            {loadingProjects ? (
              <Loader2 className="h-4 w-4 animate-spin text-neutral-400" />
            ) : projects.length === 0 ? (
              <span className="text-sm text-neutral-400">No projects found</span>
            ) : (
              <select
                className="text-sm border border-neutral-200 rounded px-3 py-1.5 bg-white text-neutral-700 focus:outline-none focus:ring-1 focus:ring-blue-400"
                value={effectiveProjectId}
                onChange={(e) => setSelectedProjectId(e.target.value)}
              >
                {projects.map((p) => (
                  <option key={p.project_id} value={p.project_id}>
                    {p.project_name} (Score: {p.score.toFixed(1)})
                  </option>
                ))}
              </select>
            )}
          </div>
        </CardContent>
      </Card>

      {!effectiveProjectId ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-20 text-center">
            <Brain className="h-10 w-10 text-neutral-300 mb-3" />
            <h3 className="text-base font-semibold text-neutral-700 mb-1">
              No projects available
            </h3>
            <p className="text-sm text-neutral-400 max-w-xs">
              Signal scores must be calculated before advisor guidance is available.
            </p>
          </CardContent>
        </Card>
      ) : (
        <>
          {/* Tabbed guidance */}
          <Tabs defaultValue="financing">
            <TabsList>
              <TabsTrigger value="financing">Financing Readiness</TabsTrigger>
              <TabsTrigger value="positioning">Market Positioning</TabsTrigger>
              <TabsTrigger value="milestones">Milestone Plan</TabsTrigger>
              <TabsTrigger value="regulatory">Regulatory</TabsTrigger>
            </TabsList>

            <TabsContent value="financing" className="mt-5">
              <FinancingTab projectId={effectiveProjectId} />
            </TabsContent>

            <TabsContent value="positioning" className="mt-5">
              <PositioningTab projectId={effectiveProjectId} />
            </TabsContent>

            <TabsContent value="milestones" className="mt-5">
              <MilestonesTab projectId={effectiveProjectId} />
            </TabsContent>

            <TabsContent value="regulatory" className="mt-5">
              <RegulatoryTab projectId={effectiveProjectId} />
            </TabsContent>
          </Tabs>

          {/* Free-form query */}
          <AdvisorQueryBox projectId={effectiveProjectId} />
        </>
      )}
    </div>
  );
}
