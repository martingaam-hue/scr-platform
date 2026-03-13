"use client";

import React from "react";
import { TrendingUp, TrendingDown, Minus } from "lucide-react";
import { cn } from "@scr/ui";

function scoreColor(s: number): string {
  if (s >= 80) return "#22c55e";
  if (s >= 70) return "#3b82f6";
  if (s >= 60) return "#f59e0b";
  if (s >= 50) return "#eab308";
  return "#ef4444";
}

interface SignalScoreHeroProps {
  avgScore: number;
  totalProjects: number;
  investmentReady: number;
  needsAttention: number;
  previousScore?: number;
  label?: string;
  subtitle?: string;
}

export function SignalScoreHero({
  avgScore,
  totalProjects,
  investmentReady,
  needsAttention,
  previousScore,
  label = "Portfolio Signal Score",
  subtitle = "Higher score = more investment ready",
}: SignalScoreHeroProps) {
  const score = Math.round(avgScore);
  const color = scoreColor(score);
  const size = 200;
  const sw = 14;
  const r = (size - sw) / 2;
  const circ = 2 * Math.PI * r;
  const pct = Math.min(Math.max(score, 0), 100) / 100;
  const offset = circ * (1 - pct);
  const cx = size / 2;

  const diff = previousScore !== undefined ? score - Math.round(previousScore) : null;

  type Stat = {
    label: string;
    value: number;
    colorClass?: string;
    colorStyle?: string;
    borderClass: string;
    bgClass: string;
    sub?: string;
  };

  const stats: Stat[] = [
    { label: "Total Projects",   value: totalProjects,   colorClass: "text-blue-700",  borderClass: "border-blue-100",  bgClass: "bg-blue-50" },
    { label: "Investment Ready", value: investmentReady,  colorClass: "text-green-700", borderClass: "border-green-100", bgClass: "bg-green-50", sub: "score ≥ 80" },
    { label: "Avg Score",        value: score,            colorStyle: color,             borderClass: "border-neutral-200", bgClass: "bg-white" },
    { label: "Needs Attention",  value: needsAttention,   colorClass: "text-red-700",   borderClass: "border-red-100",   bgClass: "bg-red-50",  sub: "score < 60" },
  ];

  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-5 items-stretch">
      {/* Left — large hero ring (~60% width) */}
      <div className="lg:col-span-3 flex flex-col items-center justify-center rounded-xl border border-neutral-200 bg-white p-8 shadow-sm">
        <div className="relative">
          <svg width={size} height={size} className="rotate-[-90deg]">
            <circle cx={cx} cy={cx} r={r} fill="none" stroke="#e5e7eb" strokeWidth={sw} />
            <circle
              cx={cx}
              cy={cx}
              r={r}
              fill="none"
              stroke={color}
              strokeWidth={sw}
              strokeDasharray={circ}
              strokeDashoffset={offset}
              strokeLinecap="round"
              style={{ transition: "stroke-dashoffset 800ms ease-out" }}
            />
          </svg>
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <span
              className="font-bold tabular-nums leading-none"
              style={{ fontSize: "72px", color }}
            >
              {score}
            </span>
          </div>
        </div>

        {diff !== null && (
          <div className="mt-2 flex items-center gap-1 text-sm">
            {diff > 0 ? (
              <>
                <TrendingUp className="h-4 w-4 text-green-500" />
                <span className="text-green-600">+{diff} from last month</span>
              </>
            ) : diff < 0 ? (
              <>
                <TrendingDown className="h-4 w-4 text-red-500" />
                <span className="text-red-600">{diff} from last month</span>
              </>
            ) : (
              <>
                <Minus className="h-4 w-4 text-neutral-400" />
                <span className="text-neutral-400">No change</span>
              </>
            )}
          </div>
        )}

        <p className="mt-3 text-sm font-medium text-neutral-700">{label}</p>
        <p className="mt-1 text-xs text-neutral-400">{subtitle}</p>
      </div>

      {/* Right — 2×2 stat grid (~40% width) */}
      <div className="lg:col-span-2 grid grid-cols-2 gap-3">
        {stats.map(({ label: statLabel, value, colorClass, colorStyle, borderClass, bgClass, sub }) => (
          <div
            key={statLabel}
            className={cn("flex flex-col justify-center rounded-xl border p-4", bgClass, borderClass)}
          >
            <p
              className={cn("text-3xl font-bold tabular-nums", colorClass)}
              style={colorStyle ? { color: colorStyle } : undefined}
            >
              {value}
            </p>
            <p className="mt-1 text-xs text-neutral-500">{statLabel}</p>
            {sub && <p className="mt-0.5 text-[10px] text-neutral-400">{sub}</p>}
          </div>
        ))}
      </div>
    </div>
  );
}
