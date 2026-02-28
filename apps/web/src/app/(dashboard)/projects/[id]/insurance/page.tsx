"use client";

import { useParams, useRouter } from "next/navigation";
import { ArrowLeft, RefreshCw, ShieldCheck, Trash2 } from "lucide-react";
import {
  Badge,
  Button,
  Card,
  CardContent,
  EmptyState,
  ScoreGauge,
} from "@scr/ui";
import { useProject } from "@/lib/projects";
import {
  useInsuranceImpact,
  useInsuranceQuotes,
  useInsurancePolicies,
  useDeleteQuote,
  useDeletePolicy,
  COVERAGE_LABELS,
  ADEQUACY_BADGE,
  PRIORITY_BADGE,
  type CoverageRecommendation,
} from "@/lib/insurance";
import { AIFeedback } from "@/components/ai-feedback";

// ── Coverage adequacy badge ───────────────────────────────────────────────────

function AdequacyBadge({ value }: { value: string }) {
  const variant = (ADEQUACY_BADGE[value] ?? "neutral") as
    | "success"
    | "warning"
    | "error"
    | "info"
    | "neutral";
  return (
    <Badge variant={variant}>
      {value.charAt(0).toUpperCase() + value.slice(1)}
    </Badge>
  );
}

// ── Recommendation card ───────────────────────────────────────────────────────

function RecommendationCard({ rec }: { rec: CoverageRecommendation }) {
  const variant = (PRIORITY_BADGE[rec.priority] ?? "neutral") as
    | "error"
    | "warning"
    | "info"
    | "neutral";
  return (
    <div className="rounded-lg border border-neutral-200 bg-white p-4">
      <div className="mb-1 flex items-center justify-between gap-2">
        <span className="font-medium text-neutral-900">
          {COVERAGE_LABELS[rec.policy_type] ?? rec.policy_type}
        </span>
        <div className="flex items-center gap-2">
          {rec.is_mandatory && (
            <Badge variant="error" className="text-xs">
              Mandatory
            </Badge>
          )}
          <Badge variant={variant} className="capitalize text-xs">
            {rec.priority}
          </Badge>
        </div>
      </div>
      <p className="text-sm text-neutral-600">{rec.rationale}</p>
      <p className="mt-1 text-xs text-neutral-400">
        Typical coverage: {(rec.typical_coverage_pct * 100).toFixed(0)}% of
        project value
      </p>
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function InsurancePage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const projectId = params.id;

  const { data: project } = useProject(projectId);
  const {
    data: impact,
    isLoading,
    refetch,
    isFetching,
  } = useInsuranceImpact(projectId);
  const { data: quotes = [] } = useInsuranceQuotes(projectId);
  const { data: policies = [] } = useInsurancePolicies(projectId);
  const deleteQuote = useDeleteQuote();
  const deletePolicy = useDeletePolicy();

  return (
    <div className="mx-auto max-w-5xl space-y-6 p-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => router.push(`/projects/${projectId}`)}
          >
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <div>
            <h1 className="text-2xl font-bold text-neutral-900">
              Insurance Analysis
            </h1>
            {project && (
              <p className="text-sm text-neutral-500">{project.name}</p>
            )}
          </div>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={() => refetch()}
          disabled={isFetching}
        >
          <RefreshCw
            className={`mr-2 h-4 w-4 ${isFetching ? "animate-spin" : ""}`}
          />
          Refresh
        </Button>
      </div>

      {isLoading ? (
        <div className="grid gap-4 sm:grid-cols-3">
          {[1, 2, 3].map((i) => (
            <Card key={i}>
              <CardContent className="h-28 animate-pulse rounded bg-neutral-100" />
            </Card>
          ))}
        </div>
      ) : !impact ? (
        <EmptyState
          icon={<ShieldCheck className="h-10 w-10" />}
          title="No insurance analysis"
          description="Click Refresh to generate an AI-powered insurance coverage analysis for this project."
        />
      ) : (
        <>
          {/* KPI cards */}
          <div className="grid gap-4 sm:grid-cols-3">
            <Card>
              <CardContent className="pt-6 text-center">
                <ScoreGauge score={impact.risk_reduction_score} />
                <p className="mt-2 text-sm font-medium text-neutral-600">
                  Risk Reduction Score
                </p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="flex flex-col items-center justify-center gap-2 pt-6">
                <AdequacyBadge value={impact.coverage_adequacy} />
                <p className="text-sm font-medium text-neutral-600">
                  Coverage Adequacy
                </p>
                <p className="text-2xl font-bold text-neutral-900">
                  {impact.estimated_annual_premium_pct.toFixed(2)}%
                </p>
                <p className="text-xs text-neutral-500">
                  Annual premium (% of investment)
                </p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="flex flex-col items-center justify-center gap-2 pt-6">
                <p className="text-2xl font-bold text-neutral-900">
                  {impact.irr_impact_bps} bps
                </p>
                <p className="text-sm font-medium text-neutral-600">
                  IRR Impact
                </p>
                <p className="text-xs text-neutral-500">
                  NPV cost:{" "}
                  {new Intl.NumberFormat("en-US", {
                    style: "currency",
                    currency: impact.currency,
                    maximumFractionDigits: 0,
                  }).format(impact.npv_premium_cost)}
                </p>
              </CardContent>
            </Card>
          </div>

          {/* AI Narrative */}
          <Card>
            <CardContent className="pt-6">
              <h2 className="mb-3 text-lg font-semibold text-neutral-900">
                AI Assessment
              </h2>
              <p className="whitespace-pre-line text-sm leading-relaxed text-neutral-700">
                {impact.ai_narrative}
              </p>
              <AIFeedback
                taskType="insurance_risk_impact"
                entityId={projectId}
                className="mt-4"
              />
            </CardContent>
          </Card>

          {/* Recommendations */}
          {impact.recommendations.length > 0 && (
            <Card>
              <CardContent className="pt-6">
                <h2 className="mb-4 text-lg font-semibold text-neutral-900">
                  Coverage Recommendations
                </h2>
                <div className="space-y-3">
                  {impact.recommendations.map((rec) => (
                    <RecommendationCard key={rec.policy_type} rec={rec} />
                  ))}
                </div>
              </CardContent>
            </Card>
          )}

          {/* Uncovered risks */}
          {impact.uncovered_risk_areas.length > 0 && (
            <Card>
              <CardContent className="pt-6">
                <h2 className="mb-3 text-lg font-semibold text-neutral-900">
                  Uncovered Risk Areas
                </h2>
                <div className="flex flex-wrap gap-2">
                  {impact.uncovered_risk_areas.map((area) => (
                    <Badge key={area} variant="warning">
                      {area}
                    </Badge>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}
        </>
      )}

      {/* Quotes */}
      <Card>
        <CardContent className="pt-6">
          <h2 className="mb-4 text-lg font-semibold text-neutral-900">
            Insurance Quotes
          </h2>
          {quotes.length === 0 ? (
            <p className="text-sm text-neutral-500">
              No quotes recorded yet.
            </p>
          ) : (
            <div className="space-y-2">
              {quotes.map((q) => (
                <div
                  key={q.id}
                  className="flex items-center justify-between rounded-lg border border-neutral-200 p-3"
                >
                  <div>
                    <p className="font-medium text-neutral-900">
                      {q.provider_name}
                    </p>
                    <p className="text-xs text-neutral-500">
                      {COVERAGE_LABELS[q.coverage_type] ?? q.coverage_type} ·{" "}
                      {q.currency} {parseFloat(q.quoted_premium).toLocaleString()}{" "}
                      / yr
                    </p>
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => deleteQuote.mutate(q.id)}
                    disabled={deleteQuote.isPending}
                  >
                    <Trash2 className="h-4 w-4 text-red-500" />
                  </Button>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Policies */}
      <Card>
        <CardContent className="pt-6">
          <h2 className="mb-4 text-lg font-semibold text-neutral-900">
            Active Policies
          </h2>
          {policies.length === 0 ? (
            <p className="text-sm text-neutral-500">
              No active policies recorded yet.
            </p>
          ) : (
            <div className="space-y-2">
              {policies.map((p) => (
                <div
                  key={p.id}
                  className="flex items-center justify-between rounded-lg border border-neutral-200 p-3"
                >
                  <div>
                    <p className="font-medium text-neutral-900">
                      {p.policy_number} · {p.provider_name}
                    </p>
                    <p className="text-xs text-neutral-500">
                      {COVERAGE_LABELS[p.coverage_type] ?? p.coverage_type} ·
                      Expires {p.end_date}
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge
                      variant={p.status === "active" ? "success" : "neutral"}
                    >
                      {p.status}
                    </Badge>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => deletePolicy.mutate(p.id)}
                      disabled={deletePolicy.isPending}
                    >
                      <Trash2 className="h-4 w-4 text-red-500" />
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
