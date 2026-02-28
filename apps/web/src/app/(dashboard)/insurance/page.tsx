"use client";

import { useState } from "react";
import {
  AlertTriangle,
  CheckCircle2,
  DollarSign,
  Info,
  Loader2,
  Shield,
  ShieldAlert,
  ShieldCheck,
  TrendingDown,
} from "lucide-react";
import {
  Badge,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  EmptyState,
} from "@scr/ui";
import {
  useInsuranceImpact,
  type CoverageRecommendation,
} from "@/lib/insurance";
import { useProjects } from "@/lib/projects";

// ── Helpers ─────────────────────────────────────────────────────────────────

const ADEQUACY_CONFIG: Record<
  string,
  { variant: "success" | "warning" | "error" | "neutral"; icon: React.ReactNode }
> = {
  excellent: { variant: "success", icon: <ShieldCheck className="h-4 w-4" /> },
  good: { variant: "success", icon: <ShieldCheck className="h-4 w-4" /> },
  partial: { variant: "warning", icon: <Shield className="h-4 w-4" /> },
  insufficient: { variant: "error", icon: <ShieldAlert className="h-4 w-4" /> },
};

const PRIORITY_COLORS: Record<string, string> = {
  critical: "bg-red-100 text-red-700 border-red-200",
  high: "bg-orange-100 text-orange-700 border-orange-200",
  medium: "bg-yellow-100 text-yellow-700 border-yellow-200",
  low: "bg-gray-100 text-gray-600 border-gray-200",
};

function formatCurrency(value: number, currency: string) {
  if (value >= 1_000_000) return `${currency} ${(value / 1_000_000).toFixed(1)}M`;
  if (value >= 1_000) return `${currency} ${(value / 1_000).toFixed(0)}K`;
  return `${currency} ${value.toFixed(0)}`;
}

// ── Coverage Card ────────────────────────────────────────────────────────────

function CoverageCard({ rec }: { rec: CoverageRecommendation }) {
  return (
    <div
      className={`rounded-xl border p-4 ${PRIORITY_COLORS[rec.priority] ?? "bg-gray-50 border-gray-200"}`}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <p className="font-semibold text-sm">{rec.label}</p>
            {rec.is_mandatory && (
              <span className="text-[10px] font-bold uppercase tracking-wide bg-white/60 px-1.5 py-0.5 rounded">
                Required
              </span>
            )}
          </div>
          <p className="text-xs mt-1 opacity-80">{rec.rationale}</p>
        </div>
        <div className="flex-shrink-0 text-right">
          <p className="text-xs font-bold">~{rec.typical_coverage_pct}%</p>
          <p className="text-[10px] opacity-70">of project value</p>
        </div>
      </div>
    </div>
  );
}

// ── Page ─────────────────────────────────────────────────────────────────────

export default function InsurancePage() {
  const [selectedProjectId, setSelectedProjectId] = useState("");
  const { data: projects } = useProjects({ limit: 50 });
  const { data: analysis, isLoading, error } = useInsuranceImpact(
    selectedProjectId || undefined
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-primary-100 rounded-lg">
            <Shield className="h-6 w-6 text-primary-600" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-neutral-900">
              Insurance Analysis
            </h1>
            <p className="text-sm text-neutral-500 mt-0.5">
              AI-powered coverage recommendations and risk impact for your projects
            </p>
          </div>
        </div>

        {/* Project selector */}
        <select
          className="text-sm border border-neutral-200 rounded-lg px-3 py-2 bg-white"
          value={selectedProjectId}
          onChange={(e) => setSelectedProjectId(e.target.value)}
        >
          <option value="">Select a project…</option>
          {projects?.items.map((p) => (
            <option key={p.id} value={p.id}>
              {p.name}
            </option>
          ))}
        </select>
      </div>

      {!selectedProjectId ? (
        <EmptyState
          icon={<Shield className="h-12 w-12 text-neutral-400" />}
          title="Select a project"
          description="Choose a project to see insurance coverage recommendations and risk impact analysis."
        />
      ) : isLoading ? (
        <div className="flex items-center gap-3 text-neutral-500 py-16 justify-center">
          <Loader2 className="h-5 w-5 animate-spin" />
          <span className="text-sm">Generating insurance analysis…</span>
        </div>
      ) : error || !analysis ? (
        <EmptyState
          icon={<ShieldAlert className="h-12 w-12 text-neutral-400" />}
          title="Analysis unavailable"
          description="Unable to generate insurance analysis for this project."
        />
      ) : (
        <>
          {/* KPI Strip */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            {[
              {
                label: "Coverage Adequacy",
                value: analysis.coverage_adequacy,
                icon: (ADEQUACY_CONFIG[analysis.coverage_adequacy]?.icon ?? <Shield className="h-5 w-5" />),
                sub: null,
                highlight: analysis.coverage_adequacy,
              },
              {
                label: "Risk Reduction",
                value: `${analysis.risk_reduction_score}/100`,
                icon: <ShieldCheck className="h-5 w-5 text-green-600" />,
                sub: "points",
                highlight: null,
              },
              {
                label: "Est. Annual Premium",
                value: formatCurrency(analysis.estimated_annual_premium, analysis.currency),
                icon: <DollarSign className="h-5 w-5 text-blue-600" />,
                sub: `${analysis.estimated_annual_premium_pct}% of project value`,
                highlight: null,
              },
              {
                label: "IRR Impact",
                value: `${analysis.irr_impact_bps} bps`,
                icon: <TrendingDown className="h-5 w-5 text-orange-600" />,
                sub: "on investor returns",
                highlight: null,
              },
            ].map(({ label, value, icon, sub, highlight }) => (
              <Card key={label}>
                <CardContent className="pt-4">
                  <div className="flex items-center gap-2 text-neutral-500 mb-2">
                    {icon}
                    <span className="text-xs font-medium">{label}</span>
                  </div>
                  {highlight ? (
                    <Badge
                      variant={
                        ADEQUACY_CONFIG[highlight]?.variant ?? "neutral"
                      }
                      className="text-sm font-bold capitalize"
                    >
                      {value}
                    </Badge>
                  ) : (
                    <p className="text-xl font-bold text-neutral-900">{value}</p>
                  )}
                  {sub && <p className="text-xs text-neutral-400 mt-1">{sub}</p>}
                </CardContent>
              </Card>
            ))}
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Coverage Recommendations */}
            <Card>
              <CardHeader>
                <CardTitle className="text-sm">
                  Coverage Recommendations
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {analysis.recommendations.map((rec) => (
                    <CoverageCard key={rec.policy_type} rec={rec} />
                  ))}
                </div>
              </CardContent>
            </Card>

            {/* Analysis Panel */}
            <div className="space-y-4">
              {/* AI Narrative */}
              <Card>
                <CardHeader>
                  <CardTitle className="text-sm">Insurance Programme Summary</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-neutral-700 leading-relaxed">
                    {analysis.ai_narrative}
                  </p>
                  <p className="text-[10px] text-neutral-400 mt-3">
                    Generated by Claude AI · {new Date(analysis.analyzed_at).toLocaleDateString()}
                  </p>
                </CardContent>
              </Card>

              {/* Gaps */}
              {analysis.uncovered_risk_areas.length > 0 && (
                <Card>
                  <CardHeader>
                    <CardTitle className="text-sm flex items-center gap-2">
                      <AlertTriangle className="h-4 w-4 text-orange-500" />
                      Coverage Gaps
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <ul className="space-y-2">
                      {analysis.uncovered_risk_areas.map((gap) => (
                        <li
                          key={gap}
                          className="flex items-start gap-2 text-sm text-neutral-700"
                        >
                          <span className="mt-0.5 text-orange-400 flex-shrink-0">•</span>
                          {gap}
                        </li>
                      ))}
                    </ul>
                  </CardContent>
                </Card>
              )}

              {/* Financial Impact */}
              <Card>
                <CardHeader>
                  <CardTitle className="text-sm flex items-center gap-2">
                    <Info className="h-4 w-4 text-blue-500" />
                    Financial Impact
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-3 text-sm">
                  <div className="flex justify-between text-neutral-600">
                    <span>Total Project Investment</span>
                    <span className="font-semibold">
                      {formatCurrency(analysis.total_investment, analysis.currency)}
                    </span>
                  </div>
                  <div className="flex justify-between text-neutral-600">
                    <span>Annual Premium</span>
                    <span className="font-semibold text-orange-600">
                      −{formatCurrency(analysis.estimated_annual_premium, analysis.currency)}
                    </span>
                  </div>
                  <div className="flex justify-between text-neutral-600">
                    <span>NPV of Premium (20yr)</span>
                    <span className="font-semibold text-orange-600">
                      −{formatCurrency(analysis.npv_premium_cost, analysis.currency)}
                    </span>
                  </div>
                  <div className="border-t pt-2 flex justify-between">
                    <span className="font-medium">IRR Dilution</span>
                    <span className="font-bold text-orange-600">
                      {Math.abs(analysis.irr_impact_bps)} bps
                    </span>
                  </div>
                </CardContent>
              </Card>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
