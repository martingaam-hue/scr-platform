"use client";

import Link from "next/link";
import {
  BarChart3,
  Briefcase,
  TrendingUp,
  ArrowRight,
  Activity,
  DollarSign,
  PieChart,
} from "lucide-react";
import { Card, CardContent } from "@scr/ui";
import { usePipelineValue } from "@/lib/deal-flow";
import { usePortfolios } from "@/lib/portfolio";

// ── Analytics hub cards ────────────────────────────────────────────────────────

const ANALYTICS_SECTIONS = [
  {
    href: "/analytics/deal-flow",
    title: "Deal Flow Analytics",
    description:
      "Visualise your deal pipeline funnel, stage conversion rates, and time-in-stage velocity across any time window.",
    icon: TrendingUp,
    color: "text-indigo-600",
    bg: "bg-indigo-50",
    border: "border-indigo-200",
    metrics: ["Funnel conversion", "Pipeline value", "Avg velocity"],
  },
  {
    href: "/analytics/portfolio",
    title: "Portfolio Analytics",
    description:
      "Analyse allocation by sector and geography, track IRR and MOIC across holdings, and measure portfolio-level performance.",
    icon: PieChart,
    color: "text-emerald-600",
    bg: "bg-emerald-50",
    border: "border-emerald-200",
    metrics: ["NAV & MOIC", "Sector allocation", "IRR by vintage"],
  },
] as const;

// ── Summary stat hooks ─────────────────────────────────────────────────────────

function SummaryKpis() {
  const { data: pipeline } = usePipelineValue();
  const { data: portfolioList } = usePortfolios();

  const portfolioCount = portfolioList?.total ?? 0;
  const totalPipeline = pipeline
    ? Object.values(pipeline.by_stage).reduce((a, b) => a + b, 0)
    : null;
  const stageCount = pipeline ? Object.keys(pipeline.by_stage).length : null;

  return (
    <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
      {[
        {
          label: "Total Pipeline Value",
          value: totalPipeline != null
            ? `€${(totalPipeline / 1_000_000).toFixed(1)}M`
            : "—",
          icon: DollarSign,
          color: "text-indigo-600",
          bg: "bg-indigo-50",
        },
        {
          label: "Active Stages",
          value: stageCount != null ? String(stageCount) : "—",
          icon: Activity,
          color: "text-blue-600",
          bg: "bg-blue-50",
        },
        {
          label: "Portfolios",
          value: String(portfolioCount),
          icon: Briefcase,
          color: "text-emerald-600",
          bg: "bg-emerald-50",
        },
        {
          label: "Pipeline (this month)",
          value: pipeline
            ? `€${(pipeline.total / 1_000_000).toFixed(1)}M`
            : "—",
          icon: BarChart3,
          color: "text-purple-600",
          bg: "bg-purple-50",
        },
      ].map(({ label, value, icon: Icon, color, bg }) => (
        <Card key={label}>
          <CardContent className="p-4 flex items-start gap-3">
            <div className={`p-2 rounded-lg ${bg}`}>
              <Icon className={`h-4 w-4 ${color}`} />
            </div>
            <div>
              <p className="text-xs text-gray-500">{label}</p>
              <p className={`text-xl font-bold mt-0.5 ${color}`}>{value}</p>
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function AnalyticsPage() {
  return (
    <div className="p-6 space-y-8 max-w-4xl mx-auto">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-semibold text-gray-900 flex items-center gap-2">
          <BarChart3 className="h-6 w-6 text-indigo-500" />
          Analytics
        </h1>
        <p className="text-sm text-gray-500 mt-0.5">
          Insights across your deal pipeline and investment portfolio
        </p>
      </div>

      {/* Live KPIs */}
      <SummaryKpis />

      {/* Navigation cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
        {ANALYTICS_SECTIONS.map((section) => {
          const Icon = section.icon;
          return (
            <Link key={section.href} href={section.href} className="group block">
              <Card
                className={`h-full border ${section.border} transition-shadow hover:shadow-md`}
              >
                <CardContent className="p-6 flex flex-col gap-4 h-full">
                  <div className="flex items-center justify-between">
                    <div className={`p-3 rounded-xl ${section.bg}`}>
                      <Icon className={`h-6 w-6 ${section.color}`} />
                    </div>
                    <ArrowRight
                      className={`h-5 w-5 text-gray-300 transition-transform group-hover:translate-x-1 group-hover:${section.color}`}
                    />
                  </div>

                  <div>
                    <h2 className="font-semibold text-gray-900 text-lg">
                      {section.title}
                    </h2>
                    <p className="text-sm text-gray-500 mt-1 leading-relaxed">
                      {section.description}
                    </p>
                  </div>

                  <div className="mt-auto flex flex-wrap gap-2">
                    {section.metrics.map((m) => (
                      <span
                        key={m}
                        className={`text-xs px-2 py-0.5 rounded-full ${section.bg} ${section.color} font-medium`}
                      >
                        {m}
                      </span>
                    ))}
                  </div>
                </CardContent>
              </Card>
            </Link>
          );
        })}
      </div>

      {/* Quick links */}
      <div className="rounded-xl border border-gray-200 bg-gray-50 p-5">
        <p className="text-xs font-semibold uppercase tracking-wide text-gray-400 mb-3">
          Related Tools
        </p>
        <div className="flex flex-wrap gap-3">
          {[
            { href: "/screener", label: "Smart Screener" },
            { href: "/reports", label: "Reports" },
            { href: "/risk", label: "Risk Analysis" },
            { href: "/comps", label: "Comparable Deals" },
            { href: "/valuations", label: "Valuations" },
          ].map(({ href, label }) => (
            <Link
              key={href}
              href={href}
              className="flex items-center gap-1.5 rounded-lg border border-gray-200 bg-white px-3 py-1.5 text-sm text-gray-600 hover:border-indigo-200 hover:text-indigo-700 transition-colors"
            >
              {label}
              <ArrowRight className="h-3.5 w-3.5" />
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
}
