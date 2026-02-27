"use client";

import * as React from "react";
import { cn } from "../lib/utils";

function scoreColor(score: number): string {
  if (score < 40) return "#C62828";
  if (score < 60) return "#F57C00";
  if (score < 80) return "#4EB457";
  return "#2E7D32";
}

export interface ScoreGaugeProps extends React.HTMLAttributes<HTMLDivElement> {
  score: number;
  size?: number;
  strokeWidth?: number;
  label?: string;
}

function ScoreGauge({
  score,
  size = 120,
  strokeWidth = 10,
  label = "Signal Score",
  className,
  ...props
}: ScoreGaugeProps) {
  const clamped = Math.max(0, Math.min(100, Math.round(score)));
  const radius = (size - strokeWidth) / 2;
  // Semicircle: 180 degrees
  const circumference = Math.PI * radius;
  const offset = circumference - (clamped / 100) * circumference;
  const color = scoreColor(clamped);

  return (
    <div
      className={cn("flex flex-col items-center", className)}
      {...props}
    >
      <svg
        width={size}
        height={size / 2 + strokeWidth}
        viewBox={`0 0 ${size} ${size / 2 + strokeWidth}`}
        className="overflow-visible"
      >
        {/* Background arc */}
        <path
          d={describeArc(size / 2, size / 2, radius, 180, 360)}
          fill="none"
          stroke="currentColor"
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          className="text-neutral-200 dark:text-neutral-700"
        />
        {/* Score arc */}
        <path
          d={describeArc(size / 2, size / 2, radius, 180, 180 + (clamped / 100) * 180)}
          fill="none"
          stroke={color}
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          style={{
            transition: "stroke-dashoffset 0.6s ease",
          }}
        />
        {/* Center text */}
        <text
          x={size / 2}
          y={size / 2 - 4}
          textAnchor="middle"
          dominantBaseline="middle"
          className="fill-neutral-900 font-bold dark:fill-neutral-100"
          style={{ fontSize: size * 0.28 }}
        >
          {clamped}
        </text>
      </svg>
      {label && (
        <p className="mt-1 text-xs font-medium text-neutral-500 dark:text-neutral-400">
          {label}
        </p>
      )}
    </div>
  );
}

function polarToCartesian(cx: number, cy: number, r: number, deg: number) {
  const rad = ((deg - 90) * Math.PI) / 180;
  return { x: cx + r * Math.cos(rad), y: cy + r * Math.sin(rad) };
}

function describeArc(
  cx: number,
  cy: number,
  r: number,
  startAngle: number,
  endAngle: number
) {
  const start = polarToCartesian(cx, cy, r, endAngle);
  const end = polarToCartesian(cx, cy, r, startAngle);
  const largeArc = endAngle - startAngle <= 180 ? "0" : "1";
  return `M ${start.x} ${start.y} A ${r} ${r} 0 ${largeArc} 0 ${end.x} ${end.y}`;
}

export { ScoreGauge };
