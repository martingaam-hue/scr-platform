"use client";

import React, { useState } from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  LabelList,
  PieChart,
  Pie,
  Cell,
  Legend,
} from "recharts";
import { cn } from "@scr/ui";
import {
  useFunnelData,
  usePipelineValue,
  useVelocity,
  stageLabel,
  formatCurrency,
  type StageCount,
  type AvgTimeInStage,
} from "@/lib/deal-flow";

// ── Period Options ─────────────────────────────────────────────────────────

const PERIODS = [
  { label: "30 days", value: 30 },
  { label: "90 days", value: 90 },
  { label: "180 days", value: 180 },
  { label: "1 year", value: 365 },
] as const;

// ── Colour palette ─────────────────────────────────────────────────────────

const BAR_COLOUR = "#4f46e5"; // indigo-600
const PIE_COLOURS = [
  "#4f46e5",
  "#7c3aed",
  "#db2777",
  "#ea580c",
  "#ca8a04",
  "#16a34a",
  "#0891b2",
];

// ── KPI Card ───────────────────────────────────────────────────────────────

function KpiCard({
  label,
  value,
  sub,
}: {
  label: string;
  value: string | number;
  sub?: string;
}) {
  return (
    <div className="rounded-xl border border-neutral-200 bg-white p-5 shadow-sm dark:border-neutral-800 dark:bg-neutral-900">
      <p className="text-sm font-medium text-neutral-500 dark:text-neutral-400">
        {label}
      </p>
      <p className="mt-1 text-3xl font-bold text-neutral-900 dark:text-white">
        {value}
      </p>
      {sub && (
        <p className="mt-0.5 text-xs text-neutral-400 dark:text-neutral-500">
          {sub}
        </p>
      )}
    </div>
  );
}

// ── Chart Card wrapper ─────────────────────────────────────────────────────

function ChartCard({
  title,
  children,
  className,
}: {
  title: string;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "rounded-xl border border-neutral-200 bg-white p-6 shadow-sm dark:border-neutral-800 dark:bg-neutral-900",
        className
      )}
    >
      <h2 className="mb-4 text-base font-semibold text-neutral-800 dark:text-neutral-100">
        {title}
      </h2>
      {children}
    </div>
  );
}

// ── Funnel Chart ───────────────────────────────────────────────────────────

function FunnelChart({ stageCounts }: { stageCounts: StageCount[] }) {
  const data = stageCounts
    .filter((s) => s.stage !== "passed")
    .map((s) => ({ name: stageLabel(s.stage), count: s.count }));

  return (
    <ResponsiveContainer width="100%" height={320}>
      <BarChart
        data={data}
        layout="vertical"
        margin={{ top: 0, right: 80, left: 20, bottom: 0 }}
      >
        <CartesianGrid strokeDasharray="3 3" horizontal={false} />
        <XAxis
          type="number"
          tick={{ fontSize: 12 }}
          tickLine={false}
          axisLine={false}
          allowDecimals={false}
        />
        <YAxis
          type="category"
          dataKey="name"
          tick={{ fontSize: 12 }}
          tickLine={false}
          axisLine={false}
          width={90}
        />
        <Tooltip
          cursor={{ fill: "rgba(79,70,229,0.07)" }}
          contentStyle={{ borderRadius: 8, fontSize: 13 }}
          formatter={(value: number) => [value, "Deals"]}
        />
        <Bar dataKey="count" fill={BAR_COLOUR} radius={[0, 4, 4, 0]}>
          <LabelList
            dataKey="count"
            position="right"
            style={{ fontSize: 12, fill: "#6b7280", fontWeight: 600 }}
          />
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

// ── Pipeline Value Chart ───────────────────────────────────────────────────

function PipelineValueChart({ byStage }: { byStage: Record<string, number> }) {
  const data = Object.entries(byStage)
    .filter(([, v]) => v > 0)
    .map(([stage, value]) => ({ name: stageLabel(stage), value }));

  if (data.length === 0) {
    return (
      <p className="py-8 text-center text-sm text-neutral-400">
        No pipeline value data yet.
      </p>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={260}>
      <BarChart data={data} margin={{ top: 4, right: 20, left: 0, bottom: 20 }}>
        <CartesianGrid strokeDasharray="3 3" vertical={false} />
        <XAxis
          dataKey="name"
          tick={{ fontSize: 11 }}
          tickLine={false}
          axisLine={false}
          angle={-30}
          textAnchor="end"
          interval={0}
        />
        <YAxis
          tick={{ fontSize: 11 }}
          tickLine={false}
          axisLine={false}
          tickFormatter={(v: number) => formatCurrency(v)}
        />
        <Tooltip
          cursor={{ fill: "rgba(79,70,229,0.07)" }}
          contentStyle={{ borderRadius: 8, fontSize: 13 }}
          formatter={(v: number) => [formatCurrency(v), "Pipeline value"]}
        />
        <Bar dataKey="value" fill="#7c3aed" radius={[4, 4, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}

// ── Time In Stage Chart ────────────────────────────────────────────────────

function TimeInStageChart({ stages }: { stages: AvgTimeInStage[] }) {
  const data = stages
    .filter((s) => s.avg_days !== null)
    .map((s) => ({ name: stageLabel(s.stage), avg_days: s.avg_days! }));

  if (data.length === 0) {
    return (
      <p className="py-8 text-center text-sm text-neutral-400">
        Not enough transition history yet.
      </p>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={260}>
      <BarChart data={data} margin={{ top: 4, right: 20, left: 0, bottom: 20 }}>
        <CartesianGrid strokeDasharray="3 3" vertical={false} />
        <XAxis
          dataKey="name"
          tick={{ fontSize: 11 }}
          tickLine={false}
          axisLine={false}
          angle={-30}
          textAnchor="end"
          interval={0}
        />
        <YAxis
          tick={{ fontSize: 11 }}
          tickLine={false}
          axisLine={false}
          unit=" d"
        />
        <Tooltip
          cursor={{ fill: "rgba(79,70,229,0.07)" }}
          contentStyle={{ borderRadius: 8, fontSize: 13 }}
          formatter={(v: number) => [`${v.toFixed(1)} days`, "Avg time"]}
        />
        <Bar dataKey="avg_days" fill="#0891b2" radius={[4, 4, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}

// ── Drop-off Pie Chart ─────────────────────────────────────────────────────

function DropOffPieChart({ reasons }: { reasons: Record<string, number> }) {
  const data = Object.entries(reasons).map(([name, value]) => ({
    name,
    value,
  }));

  if (data.length === 0) return null;

  return (
    <ChartCard title="Drop-off Reasons" className="col-span-1">
      <ResponsiveContainer width="100%" height={280}>
        <PieChart>
          <Pie
            data={data}
            cx="50%"
            cy="45%"
            outerRadius={90}
            dataKey="value"
            label={({ name, percent }) =>
              `${name} (${(percent * 100).toFixed(0)}%)`
            }
            labelLine={false}
          >
            {data.map((_entry, index) => (
              <Cell
                key={index}
                fill={PIE_COLOURS[index % PIE_COLOURS.length]}
              />
            ))}
          </Pie>
          <Legend wrapperStyle={{ fontSize: 12 }} />
          <Tooltip
            contentStyle={{ borderRadius: 8, fontSize: 13 }}
            formatter={(v: number) => [v, "Deals"]}
          />
        </PieChart>
      </ResponsiveContainer>
    </ChartCard>
  );
}

// ── Conversion Steps ───────────────────────────────────────────────────────

function ConversionTable({
  conversions,
}: {
  conversions: Array<{
    from_stage: string;
    to_stage: string;
    from_count: number;
    to_count: number;
    conversion_rate: number;
  }>;
}) {
  const nonzero = conversions.filter((c) => c.from_count > 0);
  if (nonzero.length === 0) return null;

  return (
    <div className="mt-4 overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-neutral-100 dark:border-neutral-800">
            <th className="pb-2 text-left font-medium text-neutral-500">
              From
            </th>
            <th className="pb-2 text-left font-medium text-neutral-500">To</th>
            <th className="pb-2 text-right font-medium text-neutral-500">
              Entered
            </th>
            <th className="pb-2 text-right font-medium text-neutral-500">
              Advanced
            </th>
            <th className="pb-2 text-right font-medium text-neutral-500">
              Rate
            </th>
          </tr>
        </thead>
        <tbody>
          {nonzero.map((c) => (
            <tr
              key={`${c.from_stage}-${c.to_stage}`}
              className="border-b border-neutral-50 dark:border-neutral-800/50"
            >
              <td className="py-1.5 text-neutral-700 dark:text-neutral-300">
                {stageLabel(c.from_stage)}
              </td>
              <td className="py-1.5 text-neutral-700 dark:text-neutral-300">
                {stageLabel(c.to_stage)}
              </td>
              <td className="py-1.5 text-right text-neutral-700 dark:text-neutral-300">
                {c.from_count}
              </td>
              <td className="py-1.5 text-right text-neutral-700 dark:text-neutral-300">
                {c.to_count}
              </td>
              <td className="py-1.5 text-right font-semibold">
                <span
                  className={cn(
                    "rounded px-1.5 py-0.5 text-xs",
                    c.conversion_rate >= 0.5
                      ? "bg-green-50 text-green-700 dark:bg-green-900/20 dark:text-green-400"
                      : c.conversion_rate >= 0.2
                      ? "bg-amber-50 text-amber-700 dark:bg-amber-900/20 dark:text-amber-400"
                      : "bg-red-50 text-red-700 dark:bg-red-900/20 dark:text-red-400"
                  )}
                >
                  {(c.conversion_rate * 100).toFixed(1)}%
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ── Skeleton ───────────────────────────────────────────────────────────────

function Skeleton({ className }: { className?: string }) {
  return (
    <div
      className={cn(
        "animate-pulse rounded-md bg-neutral-100 dark:bg-neutral-800",
        className
      )}
    />
  );
}

// ── Main Page ──────────────────────────────────────────────────────────────

export default function DealFlowAnalyticsPage() {
  const [periodDays, setPeriodDays] = useState<number>(90);

  const { data: funnel, isLoading: funnelLoading } = useFunnelData(periodDays);
  const { data: pipelineValue, isLoading: pvLoading } = usePipelineValue();
  const { data: velocity, isLoading: velocityLoading } = useVelocity();

  const isLoading = funnelLoading || pvLoading || velocityLoading;

  return (
    <div className="p-6 max-w-screen-xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-neutral-900 dark:text-white">
            Deal Flow Analytics
          </h1>
          <p className="mt-1 text-sm text-neutral-500 dark:text-neutral-400">
            Stage progression, pipeline value, and deal velocity.
          </p>
        </div>

        {/* Period selector */}
        <div className="flex gap-1.5 rounded-lg border border-neutral-200 bg-neutral-50 p-1 dark:border-neutral-700 dark:bg-neutral-800">
          {PERIODS.map((p) => (
            <button
              key={p.value}
              onClick={() => setPeriodDays(p.value)}
              className={cn(
                "rounded-md px-3 py-1.5 text-xs font-medium transition-colors",
                periodDays === p.value
                  ? "bg-white text-neutral-900 shadow-sm dark:bg-neutral-700 dark:text-white"
                  : "text-neutral-500 hover:text-neutral-700 dark:text-neutral-400 dark:hover:text-neutral-200"
              )}
            >
              {p.label}
            </button>
          ))}
        </div>
      </div>

      {/* Row 1: KPI Cards */}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        {isLoading ? (
          <>
            <Skeleton className="h-28" />
            <Skeleton className="h-28" />
            <Skeleton className="h-28" />
            <Skeleton className="h-28" />
          </>
        ) : (
          <>
            <KpiCard
              label="Total Entered"
              value={funnel?.total_entered ?? 0}
              sub={`in last ${periodDays} days`}
            />
            <KpiCard
              label="Total Closed"
              value={funnel?.total_closed ?? 0}
              sub="deals successfully closed"
            />
            <KpiCard
              label="Overall Conversion"
              value={
                funnel
                  ? `${(funnel.overall_conversion_rate * 100).toFixed(1)}%`
                  : "—"
              }
              sub="discovery to closed"
            />
            <KpiCard
              label="Avg Days to Close"
              value={
                velocity?.avg_days_to_close != null
                  ? `${velocity.avg_days_to_close}d`
                  : "—"
              }
              sub="across all stages"
            />
          </>
        )}
      </div>

      {/* Row 2: Funnel Chart (full width) */}
      <ChartCard title="Deal Funnel — Deals by Stage">
        {funnelLoading ? (
          <Skeleton className="h-80" />
        ) : funnel && funnel.stage_counts.length > 0 ? (
          <>
            <FunnelChart stageCounts={funnel.stage_counts} />
            <ConversionTable conversions={funnel.conversions} />
          </>
        ) : (
          <p className="py-16 text-center text-sm text-neutral-400">
            No transition data recorded yet.
          </p>
        )}
      </ChartCard>

      {/* Row 3: Pipeline Value + Time in Stage */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <ChartCard title="Pipeline Value by Stage">
          {pvLoading ? (
            <Skeleton className="h-64" />
          ) : pipelineValue ? (
            <>
              <PipelineValueChart byStage={pipelineValue.by_stage} />
              <p className="mt-2 text-right text-xs text-neutral-400">
                Total:{" "}
                <span className="font-semibold text-neutral-700 dark:text-neutral-200">
                  {formatCurrency(pipelineValue.total)}
                </span>
              </p>
            </>
          ) : null}
        </ChartCard>

        <ChartCard title="Avg Time in Stage">
          {velocityLoading ? (
            <Skeleton className="h-64" />
          ) : velocity ? (
            <TimeInStageChart stages={velocity.by_stage} />
          ) : null}
        </ChartCard>
      </div>

      {/* Row 4: Drop-off Reasons (half width) */}
      {funnel && Object.keys(funnel.drop_off_reasons).length > 0 && (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          <DropOffPieChart reasons={funnel.drop_off_reasons} />
        </div>
      )}
    </div>
  );
}
