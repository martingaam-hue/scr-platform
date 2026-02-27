"use client";

import * as React from "react";
import {
  LineChart as RechartsLine,
  BarChart as RechartsBar,
  AreaChart as RechartsArea,
  PieChart as RechartsPie,
  Line,
  Bar,
  Area,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import { cn } from "../lib/utils";

// SCR brand palette for chart series
const CHART_COLORS = [
  "#1B3A5C", // primary
  "#C5A34E", // gold
  "#2E7D32", // success
  "#F57C00", // warning
  "#2C5F8A", // primary-light
  "#4EB457", // success-light
  "#C62828", // error
  "#9E9E9E", // neutral
];

const DONUT_COLORS = [
  "#1B3A5C",
  "#C5A34E",
  "#2E7D32",
  "#2C5F8A",
  "#F57C00",
  "#4EB457",
  "#946C31",
  "#616161",
];

interface BaseChartProps {
  data: Record<string, unknown>[];
  height?: number;
  className?: string;
}

// ── Custom tooltip ──────────────────────────────────────────────────────

function ChartTooltip({
  active,
  payload,
  label,
}: {
  active?: boolean;
  payload?: Array<{ name: string; value: number; color: string }>;
  label?: string;
}) {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-md border border-neutral-200 bg-white px-3 py-2 shadow-lg dark:border-neutral-700 dark:bg-neutral-800">
      {label && (
        <p className="mb-1 text-xs font-medium text-neutral-500">{label}</p>
      )}
      {payload.map((entry, i) => (
        <div key={i} className="flex items-center gap-2 text-sm">
          <span
            className="h-2 w-2 rounded-full"
            style={{ backgroundColor: entry.color }}
          />
          <span className="text-neutral-600 dark:text-neutral-300">
            {entry.name}:
          </span>
          <span className="font-medium text-neutral-900 dark:text-neutral-100">
            {typeof entry.value === "number"
              ? entry.value.toLocaleString()
              : entry.value}
          </span>
        </div>
      ))}
    </div>
  );
}

// ── Line Chart ──────────────────────────────────────────────────────────

interface LineChartProps extends BaseChartProps {
  xKey: string;
  yKeys: string[];
  yLabels?: Record<string, string>;
  curved?: boolean;
}

function LineChart({
  data,
  xKey,
  yKeys,
  yLabels,
  curved = true,
  height = 300,
  className,
}: LineChartProps) {
  return (
    <div className={cn("w-full", className)}>
      <ResponsiveContainer width="100%" height={height}>
        <RechartsLine data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="#E0E0E0" opacity={0.5} />
          <XAxis
            dataKey={xKey}
            tick={{ fontSize: 12, fill: "#9E9E9E" }}
            tickLine={false}
            axisLine={{ stroke: "#E0E0E0" }}
          />
          <YAxis
            tick={{ fontSize: 12, fill: "#9E9E9E" }}
            tickLine={false}
            axisLine={false}
          />
          <Tooltip content={<ChartTooltip />} />
          {yKeys.length > 1 && <Legend />}
          {yKeys.map((key, i) => (
            <Line
              key={key}
              type={curved ? "monotone" : "linear"}
              dataKey={key}
              name={yLabels?.[key] ?? key}
              stroke={CHART_COLORS[i % CHART_COLORS.length]}
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4 }}
            />
          ))}
        </RechartsLine>
      </ResponsiveContainer>
    </div>
  );
}

// ── Bar Chart ───────────────────────────────────────────────────────────

interface BarChartProps extends BaseChartProps {
  xKey: string;
  yKeys: string[];
  yLabels?: Record<string, string>;
  stacked?: boolean;
}

function BarChart({
  data,
  xKey,
  yKeys,
  yLabels,
  stacked = false,
  height = 300,
  className,
}: BarChartProps) {
  return (
    <div className={cn("w-full", className)}>
      <ResponsiveContainer width="100%" height={height}>
        <RechartsBar data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="#E0E0E0" opacity={0.5} />
          <XAxis
            dataKey={xKey}
            tick={{ fontSize: 12, fill: "#9E9E9E" }}
            tickLine={false}
            axisLine={{ stroke: "#E0E0E0" }}
          />
          <YAxis
            tick={{ fontSize: 12, fill: "#9E9E9E" }}
            tickLine={false}
            axisLine={false}
          />
          <Tooltip content={<ChartTooltip />} />
          {yKeys.length > 1 && <Legend />}
          {yKeys.map((key, i) => (
            <Bar
              key={key}
              dataKey={key}
              name={yLabels?.[key] ?? key}
              fill={CHART_COLORS[i % CHART_COLORS.length]}
              stackId={stacked ? "stack" : undefined}
              radius={[4, 4, 0, 0]}
            />
          ))}
        </RechartsBar>
      </ResponsiveContainer>
    </div>
  );
}

// ── Area Chart ──────────────────────────────────────────────────────────

interface AreaChartProps extends BaseChartProps {
  xKey: string;
  yKeys: string[];
  yLabels?: Record<string, string>;
  stacked?: boolean;
}

function AreaChart({
  data,
  xKey,
  yKeys,
  yLabels,
  stacked = false,
  height = 300,
  className,
}: AreaChartProps) {
  return (
    <div className={cn("w-full", className)}>
      <ResponsiveContainer width="100%" height={height}>
        <RechartsArea data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="#E0E0E0" opacity={0.5} />
          <XAxis
            dataKey={xKey}
            tick={{ fontSize: 12, fill: "#9E9E9E" }}
            tickLine={false}
            axisLine={{ stroke: "#E0E0E0" }}
          />
          <YAxis
            tick={{ fontSize: 12, fill: "#9E9E9E" }}
            tickLine={false}
            axisLine={false}
          />
          <Tooltip content={<ChartTooltip />} />
          {yKeys.length > 1 && <Legend />}
          {yKeys.map((key, i) => (
            <Area
              key={key}
              type="monotone"
              dataKey={key}
              name={yLabels?.[key] ?? key}
              stroke={CHART_COLORS[i % CHART_COLORS.length]}
              fill={CHART_COLORS[i % CHART_COLORS.length]}
              fillOpacity={0.15}
              stackId={stacked ? "stack" : undefined}
              strokeWidth={2}
            />
          ))}
        </RechartsArea>
      </ResponsiveContainer>
    </div>
  );
}

// ── Donut Chart ─────────────────────────────────────────────────────────

interface DonutChartProps extends BaseChartProps {
  nameKey: string;
  valueKey: string;
  innerRadius?: number;
  outerRadius?: number;
}

function DonutChart({
  data,
  nameKey,
  valueKey,
  innerRadius = 60,
  outerRadius = 90,
  height = 300,
  className,
}: DonutChartProps) {
  return (
    <div className={cn("w-full", className)}>
      <ResponsiveContainer width="100%" height={height}>
        <RechartsPie>
          <Pie
            data={data}
            dataKey={valueKey}
            nameKey={nameKey}
            cx="50%"
            cy="50%"
            innerRadius={innerRadius}
            outerRadius={outerRadius}
            paddingAngle={2}
            strokeWidth={0}
          >
            {data.map((_, i) => (
              <Cell
                key={i}
                fill={DONUT_COLORS[i % DONUT_COLORS.length]}
              />
            ))}
          </Pie>
          <Tooltip content={<ChartTooltip />} />
          <Legend
            layout="vertical"
            verticalAlign="middle"
            align="right"
            iconType="circle"
            iconSize={8}
          />
        </RechartsPie>
      </ResponsiveContainer>
    </div>
  );
}

export {
  LineChart,
  BarChart,
  AreaChart,
  DonutChart,
  CHART_COLORS,
  DONUT_COLORS,
};
