"use client";

import { useParams, useRouter } from "next/navigation";
import {
  ArrowLeft,
  Building2,
  Globe,
  TrendingUp,
} from "lucide-react";
import {
  Badge,
  Button,
  Card,
  CardContent,
  EmptyState,
  ScoreGauge,
} from "@scr/ui";
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

// ── Alignment breakdown ───────────────────────────────────────────────────

function AlignmentBreakdown({
  alignment,
}: {
  alignment: MatchingInvestor["alignment"];
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

// ── Mandate fit chips ─────────────────────────────────────────────────────

function MandateFit({ investor }: { investor: MatchingInvestor }) {
  const items: { label: string; value: string }[] = [
    {
      label: "Ticket Range",
      value: `$${Number(investor.ticket_size_min).toLocaleString()} – $${Number(investor.ticket_size_max).toLocaleString()}`,
    },
    {
      label: "Risk",
      value: investor.risk_tolerance
        ? investor.risk_tolerance.charAt(0).toUpperCase() +
          investor.risk_tolerance.slice(1)
        : "—",
    },
    {
      label: "Sectors",
      value:
        investor.sectors.length > 0
          ? investor.sectors.slice(0, 3).join(", ") +
            (investor.sectors.length > 3
              ? ` +${investor.sectors.length - 3}`
              : "")
          : "Any",
    },
    {
      label: "Geographies",
      value:
        investor.geographies.length > 0
          ? investor.geographies.slice(0, 2).join(", ") +
            (investor.geographies.length > 2
              ? ` +${investor.geographies.length - 2}`
              : "")
          : "Global",
    },
  ];

  return (
    <div className="grid grid-cols-2 gap-2 mt-3">
      {items.map((item) => (
        <div key={item.label} className="bg-neutral-50 rounded-md px-3 py-2">
          <p className="text-xs text-neutral-500">{item.label}</p>
          <p className="text-xs font-semibold text-neutral-800 truncate">
            {item.value}
          </p>
        </div>
      ))}
    </div>
  );
}

// ── Investor card ─────────────────────────────────────────────────────────

function InvestorCard({
  investor,
  projectId,
}: {
  investor: MatchingInvestor;
  projectId: string;
}) {
  const updateStatus = useUpdateMatchStatus();

  return (
    <Card className="hover:shadow-md transition-shadow">
      <CardContent className="p-5">
        {/* Header row */}
        <div className="flex items-start justify-between gap-4 mb-4">
          <div className="flex items-center gap-3 min-w-0">
            {investor.logo_url ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={investor.logo_url}
                alt={investor.investor_name}
                className="h-10 w-10 rounded-lg object-contain border border-neutral-200 bg-white"
              />
            ) : (
              <div className="h-10 w-10 rounded-lg bg-neutral-100 flex items-center justify-center">
                <Building2 className="h-5 w-5 text-neutral-400" />
              </div>
            )}
            <div className="min-w-0">
              <h3 className="font-semibold text-sm text-neutral-900 truncate">
                {investor.investor_name}
              </h3>
              {investor.mandate_name && (
                <p className="text-xs text-neutral-500 truncate">
                  {investor.mandate_name}
                </p>
              )}
            </div>
          </div>

          <div className="flex flex-col items-end gap-2 shrink-0">
            <ScoreGauge score={investor.alignment.overall} size={48} />
            <Badge variant={statusVariant(investor.status)}>
              {statusLabel(investor.status)}
            </Badge>
          </div>
        </div>

        {/* Overall alignment bar */}
        <div className="mb-4">
          <div className="flex justify-between text-xs mb-1">
            <span className="text-neutral-500">Overall Alignment</span>
            <span
              className={`font-semibold ${alignmentColor(
                investor.alignment.overall
              )}`}
            >
              {investor.alignment.overall}%
            </span>
          </div>
          <div className="h-2 bg-neutral-100 rounded-full overflow-hidden">
            <div
              className={`h-full rounded-full transition-all ${alignmentBarColor(
                investor.alignment.overall
              )}`}
              style={{ width: `${investor.alignment.overall}%` }}
            />
          </div>
        </div>

        {/* Dimension breakdown */}
        <div className="mb-4">
          <p className="text-xs font-medium text-neutral-600 mb-2">
            Dimension Scores
          </p>
          <AlignmentBreakdown alignment={investor.alignment} />
        </div>

        {/* Mandate fit */}
        <div className="mb-4">
          <p className="text-xs font-medium text-neutral-600 mb-1">
            Mandate Criteria
          </p>
          <MandateFit investor={investor} />
        </div>

        {/* Footer: initiated_by + status + actions */}
        <div className="flex items-center justify-between pt-3 border-t border-neutral-100">
          <div className="flex items-center gap-2 text-xs text-neutral-400">
            {investor.initiated_by && (
              <span>
                Initiated by{" "}
                <span className="capitalize">{investor.initiated_by}</span>
              </span>
            )}
            {investor.updated_at && (
              <span>
                · {new Date(investor.updated_at).toLocaleDateString()}
              </span>
            )}
          </div>

          {investor.match_id && (
            <select
              className="text-xs border border-neutral-200 rounded px-2 h-7 bg-white text-neutral-700"
              value={investor.status}
              onChange={(e) => {
                if (!investor.match_id) return;
                updateStatus.mutate({
                  matchId: investor.match_id,
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

// ── Activity timeline ─────────────────────────────────────────────────────

function ActivityTimeline({ investors }: { investors: MatchingInvestor[] }) {
  // Build chronological events from investors that have match activity
  const events = investors
    .filter((inv) => inv.match_id && inv.updated_at)
    .map((inv) => ({
      id: inv.match_id!,
      investor: inv.investor_name,
      status: inv.status,
      date: inv.updated_at!,
    }))
    .sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime())
    .slice(0, 20);

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
    <div className="relative pl-6">
      <div className="absolute left-2 top-0 bottom-0 w-0.5 bg-neutral-200" />
      <div className="space-y-5">
        {events.map((ev) => (
          <div key={ev.id} className="relative">
            <div className="absolute -left-6 top-1 h-3 w-3 rounded-full border-2 border-white bg-primary-500 ring-2 ring-primary-100" />
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="text-sm font-medium text-neutral-800">
                  {ev.investor}
                </p>
                <p className="text-xs text-neutral-500">
                  Status changed to{" "}
                  <Badge variant={statusVariant(ev.status)} className="text-xs ml-1">
                    {statusLabel(ev.status)}
                  </Badge>
                </p>
              </div>
              <time className="text-xs text-neutral-400 shrink-0">
                {new Date(ev.date).toLocaleDateString()}
              </time>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────

export default function ProjectMatchingPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();

  const { data: project } = useProject(id);
  const { data, isLoading } = useAllyRecommendations(id);

  return (
    <div className="p-6 max-w-screen-xl mx-auto">
      {/* Back nav */}
      <div className="mb-6">
        <button
          onClick={() => router.push(`/projects/${id}`)}
          className="flex items-center gap-1.5 text-sm text-neutral-500 hover:text-neutral-800 transition-colors mb-3"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to project
        </button>

        <h1 className="text-2xl font-bold text-neutral-900">
          Investor Matching
        </h1>
        {project && (
          <p className="text-sm text-neutral-500 mt-1">
            Investors matched to{" "}
            <span className="font-medium text-neutral-700">
              {project.name}
            </span>
          </p>
        )}
      </div>

      {/* Summary stats */}
      {data && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-6">
          <Card>
            <CardContent className="p-4">
              <p className="text-xs text-neutral-500 mb-1">Total Matches</p>
              <p className="text-2xl font-bold text-neutral-900">{data.total}</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4">
              <p className="text-xs text-neutral-500 mb-1">Interested</p>
              <p className="text-2xl font-bold text-green-600">
                {
                  data.items.filter(
                    (i) =>
                      i.status === "interested" ||
                      i.status === "intro_requested" ||
                      i.status === "engaged"
                  ).length
                }
              </p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4">
              <p className="text-xs text-neutral-500 mb-1">Avg. Alignment</p>
              <p className="text-2xl font-bold text-neutral-900">
                {data.items.length > 0
                  ? Math.round(
                      data.items.reduce(
                        (s, i) => s + i.alignment.overall,
                        0
                      ) / data.items.length
                    )
                  : 0}
                %
              </p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4">
              <p className="text-xs text-neutral-500 mb-1">Active Mandates</p>
              <p className="text-2xl font-bold text-neutral-900">
                {new Set(data.items.map((i) => i.mandate_id).filter(Boolean))
                  .size}
              </p>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Main content: 2-col layout */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Investor list (2/3 width) */}
        <div className="lg:col-span-2">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-semibold text-neutral-800">
              Matched Investors
            </h2>
            {data && (
              <span className="text-xs text-neutral-500">
                {data.total} investor{data.total !== 1 ? "s" : ""}
              </span>
            )}
          </div>

          {isLoading ? (
            <div className="flex h-64 items-center justify-center">
              <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary-600 border-t-transparent" />
            </div>
          ) : !data || data.items.length === 0 ? (
            <EmptyState
              icon={<Globe className="h-8 w-8" />}
              title="No matches yet"
              description="Investors will appear here once the matching engine scores your project against active mandates."
            />
          ) : (
            <div className="space-y-4">
              {data.items.map((investor) => (
                <InvestorCard
                  key={investor.investor_org_id}
                  investor={investor}
                  projectId={id}
                />
              ))}
            </div>
          )}
        </div>

        {/* Activity timeline (1/3 width) */}
        <div>
          <h2 className="font-semibold text-neutral-800 mb-4">
            Match Activity
          </h2>
          {isLoading ? (
            <div className="flex h-32 items-center justify-center">
              <div className="h-6 w-6 animate-spin rounded-full border-4 border-primary-600 border-t-transparent" />
            </div>
          ) : (
            <ActivityTimeline investors={data?.items ?? []} />
          )}
        </div>
      </div>
    </div>
  );
}
